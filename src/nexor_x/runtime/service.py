from __future__ import annotations

import asyncio
from dataclasses import dataclass
import re
import shutil
from typing import Any


@dataclass(slots=True)
class ManagedProcess:
    name: str
    process: asyncio.subprocess.Process | None = None
    command: tuple[str, ...] = ()
    running: bool = False
    details: str = ""


class RuntimeProcessManager:
    """Starts optional local helpers used by the one-command launcher."""

    _TUNNEL_URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

    def __init__(self, settings: Any) -> None:
        self.settings = settings
        self.ollama = ManagedProcess("ollama")
        self.cloudflared = ManagedProcess("cloudflared")
        self.public_url: str | None = None
        self._reader_tasks: list[asyncio.Task[None]] = []

    async def start_ollama(self) -> None:
        if not bool(getattr(self.settings, "ollama_autostart", True)):
            self.ollama.details = "Autostart desativado."
            return

        command = str(getattr(self.settings, "ollama_command", "ollama")).strip()
        if not shutil.which(command):
            self.ollama.details = f"Executável não encontrado: {command}"
            return

        if await self._tcp_open("127.0.0.1", 11434):
            self.ollama.running = True
            self.ollama.details = "Ollama já estava em execução."
            return

        process = await asyncio.create_subprocess_exec(
            command,
            "serve",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        self.ollama.process = process
        self.ollama.command = (command, "serve")
        self.ollama.running = True
        self.ollama.details = "Ollama iniciado pelo NEXOR X."
        self._reader_tasks.append(
            asyncio.create_task(
                self._consume_output(self.ollama, capture_tunnel=False)
            )
        )

    async def start_cloudflared(self) -> None:
        if not bool(getattr(self.settings, "cloudflared_enabled", True)):
            self.cloudflared.details = "Tunnel público desativado."
            return

        command = str(
            getattr(self.settings, "cloudflared_command", "cloudflared")
        ).strip()
        if not shutil.which(command):
            self.cloudflared.details = (
                f"Executável não encontrado: {command}. "
                "O painel local continua disponível."
            )
            return

        host = str(getattr(self.settings, "nexor_host", "127.0.0.1"))
        port = int(getattr(self.settings, "nexor_port", 8809))
        local_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
        local_url = f"http://{local_host}:{port}"

        process = await asyncio.create_subprocess_exec(
            command,
            "tunnel",
            "--no-autoupdate",
            "--url",
            local_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        self.cloudflared.process = process
        self.cloudflared.command = (
            command,
            "tunnel",
            "--no-autoupdate",
            "--url",
            local_url,
        )
        self.cloudflared.running = True
        self.cloudflared.details = "Tunnel Cloudflare iniciando."
        self._reader_tasks.append(
            asyncio.create_task(
                self._consume_output(self.cloudflared, capture_tunnel=True)
            )
        )

    async def stop(self) -> None:
        for managed in (self.cloudflared, self.ollama):
            process = managed.process
            if process is None or process.returncode is not None:
                continue
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except TimeoutError:
                process.kill()
                await process.wait()
            managed.running = False

        for task in self._reader_tasks:
            if not task.done():
                task.cancel()
        self._reader_tasks.clear()

    async def wait_for_public_url(self, timeout: float = 15.0) -> str | None:
        elapsed = 0.0
        while elapsed < timeout:
            if self.public_url:
                return self.public_url
            if (
                self.cloudflared.process is not None
                and self.cloudflared.process.returncode is not None
            ):
                return None
            await asyncio.sleep(0.2)
            elapsed += 0.2
        return self.public_url

    async def status(self) -> dict[str, Any]:
        self._refresh_state(self.ollama)
        self._refresh_state(self.cloudflared)
        host = str(getattr(self.settings, "nexor_host", "127.0.0.1"))
        port = int(getattr(self.settings, "nexor_port", 8809))
        local_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
        return {
            "local_panel_url": f"http://{local_host}:{port}",
            "public_panel_url": self.public_url,
            "ollama": {
                "running": self.ollama.running,
                "details": self.ollama.details,
            },
            "cloudflared": {
                "running": self.cloudflared.running,
                "details": self.cloudflared.details,
            },
            "live_enabled": False,
        }

    async def _consume_output(
        self,
        managed: ManagedProcess,
        *,
        capture_tunnel: bool,
    ) -> None:
        process = managed.process
        if process is None or process.stdout is None:
            return

        while True:
            line = await process.stdout.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").strip()
            if text:
                managed.details = text[-500:]
            if capture_tunnel:
                match = self._TUNNEL_URL.search(text)
                if match:
                    self.public_url = match.group(0)
                    managed.details = "Tunnel público ativo."

        self._refresh_state(managed)

    @staticmethod
    def _refresh_state(managed: ManagedProcess) -> None:
        if managed.process is not None:
            managed.running = managed.process.returncode is None

    @staticmethod
    async def _tcp_open(host: str, port: int) -> bool:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=0.5,
            )
            del reader
            writer.close()
            await writer.wait_closed()
            return True
        except (OSError, TimeoutError):
            return False

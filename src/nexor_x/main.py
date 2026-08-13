from __future__ import annotations

import asyncio

import uvicorn

from nexor_x.api.app import create_app
from nexor_x.config import get_settings
from nexor_x.kernel import Kernel
from nexor_x.logging import configure_logging
from nexor_x.runtime import RuntimeProcessManager


async def serve() -> None:
    settings = get_settings()
    configure_logging(settings.nexor_log_level)
    runtime = RuntimeProcessManager(settings)

    await runtime.start_ollama()

    kernel = Kernel(settings)
    await kernel.start()
    kernel.runtime_processes = runtime

    app = create_app(kernel)
    config = uvicorn.Config(
        app=app,
        host=settings.nexor_host,
        port=settings.nexor_port,
        log_level=settings.nexor_log_level.lower(),
    )
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())

    try:
        for _ in range(100):
            if server.started:
                break
            if server_task.done():
                await server_task
                return
            await asyncio.sleep(0.05)

        await runtime.start_cloudflared()
        public_url = await runtime.wait_for_public_url(timeout=15.0)
        status = await runtime.status()

        print("")
        print("==============================================")
        print(" NEXOR X INICIADO")
        print("==============================================")
        print(f" Painel local:  {status['local_panel_url']}")
        print(
            " Painel público: "
            + (public_url or "Cloudflared indisponível/não configurado")
        )
        print(
            " IA local: "
            + ("ATIVA" if status["ollama"]["running"] else "NÃO INICIADA")
        )
        print(f" Modo: {settings.nexor_mode.value}")
        print(" Operação real: BLOQUEADA")
        print("==============================================")
        print("")

        await server_task
    finally:
        await runtime.stop()
        await kernel.stop()


def run() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    run()

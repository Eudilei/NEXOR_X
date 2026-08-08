from __future__ import annotations

from datetime import UTC, datetime
import os
from typing import Any

from .models import UpdateRecord, UpdateStatus
from .versioning import Version


class UpdateRegistryService:
    """Runtime audit trail for versions already committed to the repository.

    GitHub Actions remains responsible for applying code updates. This service
    records what version actually started successfully at runtime.
    """

    def __init__(self, database: Any) -> None:
        self.database = database

    async def start(self) -> None:
        await self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS system_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                update_id TEXT NOT NULL,
                version TEXT NOT NULL,
                status TEXT NOT NULL,
                source TEXT NOT NULL,
                applied_at TEXT NOT NULL,
                commit_sha TEXT,
                notes TEXT NOT NULL DEFAULT ''
            )
            """
        )
        await self.database.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_system_updates_version_status
            ON system_updates(version, status)
            """
        )

    async def register_runtime_version(
        self,
        *,
        version: str,
        update_id: str | None = None,
        source: str = "runtime",
        notes: str = "",
    ) -> dict[str, Any]:
        parsed = Version.parse(version)
        normalized = str(parsed)
        existing = await self._get_version(normalized, UpdateStatus.APPLIED)
        if existing is not None:
            return existing

        commit_sha = (
            os.getenv("RENDER_GIT_COMMIT")
            or os.getenv("GITHUB_SHA")
            or os.getenv("COMMIT_SHA")
        )
        record = UpdateRecord(
            update_id=update_id or f"runtime-{normalized}",
            version=normalized,
            status=UpdateStatus.APPLIED,
            source=source,
            applied_at=datetime.now(UTC),
            commit_sha=commit_sha,
            notes=notes,
        )
        await self.database.execute(
            """
            INSERT OR IGNORE INTO system_updates(
                update_id, version, status, source, applied_at, commit_sha, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.update_id,
                record.version,
                record.status.value,
                record.source,
                record.applied_at.isoformat(),
                record.commit_sha,
                record.notes,
            ),
        )
        return (await self._get_version(normalized, UpdateStatus.APPLIED)) or record.to_dict()

    async def status(self) -> dict[str, Any]:
        await self.start()
        rows = await self.database.fetchall(
            """
            SELECT update_id, version, status, source, applied_at, commit_sha, notes
            FROM system_updates
            ORDER BY id DESC
            LIMIT 25
            """
        )
        history = [
            {
                "update_id": str(row[0]),
                "version": str(row[1]),
                "status": str(row[2]),
                "source": str(row[3]),
                "applied_at": str(row[4]),
                "commit_sha": None if row[5] is None else str(row[5]),
                "notes": str(row[6]),
            }
            for row in rows
        ]
        return {
            "state": "READY",
            "latest": None if not history else history[0],
            "history": history,
            "rollback_automatic_on_failed_tests": True,
            "runtime_live_switch_allowed": False,
        }

    async def _get_version(
        self,
        version: str,
        status: UpdateStatus,
    ) -> dict[str, Any] | None:
        await self.start()
        rows = await self.database.fetchall(
            """
            SELECT update_id, version, status, source, applied_at, commit_sha, notes
            FROM system_updates
            WHERE version = ? AND status = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (version, status.value),
        )
        if not rows:
            return None
        row = rows[0]
        return {
            "update_id": str(row[0]),
            "version": str(row[1]),
            "status": str(row[2]),
            "source": str(row[3]),
            "applied_at": str(row[4]),
            "commit_sha": None if row[5] is None else str(row[5]),
            "notes": str(row[6]),
        }

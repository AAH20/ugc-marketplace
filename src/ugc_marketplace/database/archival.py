"""Database archival strategy for UGC Marketplace."""

from __future__ import annotations

import gzip
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text

from ugc_marketplace.config.logging_config import get_logger

logger = get_logger(__name__)

# SQL identifiers cannot be bound as parameters, so any table/column name
# reaching a text() statement must be validated first. Anything that is not a
# plain (optionally schema-qualified) identifier is rejected outright rather
# than escaped -- there is no legitimate archive containing such a name.
_SQL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
_MAX_IDENTIFIER_LEN = 63  # PostgreSQL NAMEDATALEN - 1


def _validate_identifier(name: str, kind: str) -> str:
    """Validate a SQL identifier used for dynamic DDL/DML construction.

    Args:
        name: The candidate identifier.
        kind: Either ``"table"`` or ``"column"``, used in the error message.

    Returns:
        The identifier unchanged, when it is safe to interpolate.

    Raises:
        ValueError: If the identifier is empty, too long, or contains any
            character other than ``[A-Za-z0-9_$]`` after the first character.
    """
    if not isinstance(name, str) or not name:
        raise ValueError(f"Invalid SQL {kind} name: must be a non-empty string")

    if len(name) > _MAX_IDENTIFIER_LEN:
        raise ValueError(
            f"Invalid SQL {kind} name {name!r}: exceeds {_MAX_IDENTIFIER_LEN} characters"
        )

    if not _SQL_IDENTIFIER.match(name):
        raise ValueError(
            f"Invalid SQL {kind} name {name!r}: only [A-Za-z0-9_$] identifiers are allowed"
        )

    return name


class ArchivalManager:
    """Manages data archival for old records."""

    def __init__(
        self,
        engine: Any,
        archive_dir: str = "/var/lib/ugc-marketplace/archives",
        retention_days: int = 90,
    ) -> None:
        self.engine = engine
        self.archive_dir = Path(archive_dir)
        self.retention_days = retention_days
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    async def archive_old_analytics_events(self) -> dict[str, Any]:
        """Archive analytics events older than retention period."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        archive_file = (
            self.archive_dir / f"analytics_events_{cutoff_date.strftime('%Y%m')}.jsonl.gz"
        )
        async with self.engine.begin() as conn:
            result = await conn.execute(
                text(
                    "SELECT * FROM analytics_events WHERE created_at < :cutoff_date ORDER BY created_at"
                ),
                {"cutoff_date": cutoff_date},
            )
            events = [dict(row._mapping) for row in result]
            if not events:
                return {"archived": 0, "file": None}
            with gzip.open(archive_file, "wt", encoding="utf-8") as f:
                for event in events:
                    f.write(json.dumps(event, default=str) + "\n")
            await conn.execute(
                text("DELETE FROM analytics_events WHERE created_at < :cutoff_date"),
                {"cutoff_date": cutoff_date},
            )
        stats = {
            "archived": len(events),
            "file": str(archive_file),
            "size_bytes": archive_file.stat().st_size,
            "cutoff_date": cutoff_date.isoformat(),
        }
        logger.info("Archived analytics events", **stats)
        return stats

    async def archive_old_audit_logs(self) -> dict[str, Any]:
        """Archive audit logs older than retention period."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        archive_file = self.archive_dir / f"audit_log_{cutoff_date.strftime('%Y%m')}.jsonl.gz"
        async with self.engine.begin() as conn:
            result = await conn.execute(
                text("SELECT * FROM audit_log WHERE changed_at < :cutoff_date ORDER BY changed_at"),
                {"cutoff_date": cutoff_date},
            )
            logs = [dict(row._mapping) for row in result]
            if not logs:
                return {"archived": 0, "file": None}
            with gzip.open(archive_file, "wt", encoding="utf-8") as f:
                for log in logs:
                    f.write(json.dumps(log, default=str) + "\n")
            await conn.execute(
                text("DELETE FROM audit_log WHERE changed_at < :cutoff_date"),
                {"cutoff_date": cutoff_date},
            )
        stats = {
            "archived": len(logs),
            "file": str(archive_file),
            "size_bytes": archive_file.stat().st_size,
            "cutoff_date": cutoff_date.isoformat(),
        }
        logger.info("Archived audit logs", **stats)
        return stats

    async def get_archive_index(self) -> list[dict[str, Any]]:
        """Get index of all archive files."""
        archives = []
        for file in sorted(self.archive_dir.glob("*.jsonl.gz")):
            stat = file.stat()
            archives.append(
                {
                    "file": str(file),
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                }
            )
        return archives

    async def restore_from_archive(self, archive_file: str, table_name: str) -> int:
        """Restore data from archive file."""
        path = Path(archive_file)
        if not path.exists():
            raise FileNotFoundError(f"Archive file not found: {archive_file}")
        _validate_identifier(table_name, "table")

        # Parse and validate the entire archive *before* opening a transaction.
        # Validating inside the execute loop would let a malformed archive open
        # a transaction and partially insert rows before failing.
        pending: list[tuple[dict[str, Any], str]] = []
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                columns = [_validate_identifier(col, "column") for col in record.keys()]
                if not columns:
                    continue
                placeholders = [f":{col}" for col in columns]
                # Values are always bound as parameters; only validated
                # identifiers are interpolated into the statement text.
                # nosec B608 - table_name and every column are validated
                # against ^[A-Za-z_][A-Za-z0-9_$]*$ by _validate_identifier on
                # the lines above, and all values are bound as parameters.
                # Identifiers cannot be parameterised in SQL; validation is the
                # only available control, and it rejects on first match failure.
                query = text(
                    f"INSERT INTO {table_name} ({', '.join(columns)}) "  # nosec B108 B608
                    f"VALUES ({', '.join(placeholders)})"
                )
                pending.append((record, str(query)))

        restored = 0
        async with self.engine.begin() as conn:
            for record, query in pending:
                await conn.execute(text(query), record)
                restored += 1
        logger.info("Restored records from archive", count=restored, file=archive_file)
        return restored

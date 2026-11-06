# database.py

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATABASE_PATH = Path(__file__).resolve().parent / "payflow_activity.db"

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?i)(access[_-]?token|client[_-]?secret|authorization|password|api[_-]?key)"
)


def _redact_sensitive_data(value: Any) -> str:
    """Convert log data to text while removing common credential fields."""
    if isinstance(value, dict):
        safe_value = {
            key: "[REDACTED]"
            if _SENSITIVE_KEY_PATTERN.search(str(key))
            else _redact_sensitive_data(item)
            for key, item in value.items()
        }
        return json.dumps(safe_value, default=str)

    text = str(value)

    text = re.sub(
        r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+",
        r"\1[REDACTED]",
        text,
    )

    text = re.sub(
        r"(?i)(client[_-]?secret|access[_-]?token|api[_-]?key)"
        r"(\s*[:=]\s*)['\"]?[^,'\"}\s]+",
        r"\1\2[REDACTED]",
        text,
    )

    return text[:1000]


def _initialize_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_PATH, timeout=10) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                user_request TEXT NOT NULL,
                action TEXT NOT NULL,
                paypal_response TEXT
            )
            """
        )
        connection.commit()


def log_activity(
    user_request: str,
    action: str,
    paypal_response: str | dict[str, Any] | None = None,
) -> None:
    """Store a sanitized PayFlow activity record in SQLite."""
    _initialize_database()

    safe_request = _redact_sensitive_data(user_request)
    safe_response = _redact_sensitive_data(paypal_response or "")

    created_at = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DATABASE_PATH, timeout=10) as connection:
        connection.execute(
            """
            INSERT INTO activity_log (
                created_at,
                user_request,
                action,
                paypal_response
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                created_at,
                safe_request,
                str(action)[:100],
                safe_response,
            ),
        )
        connection.commit()

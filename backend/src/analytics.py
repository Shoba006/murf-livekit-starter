import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATABASE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "kural_analytics.db"
)


def initialize_analytics_database() -> None:
    """Create the call analytics database."""

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS calls (
                call_id TEXT PRIMARY KEY,
                user_id TEXT,
                outcome TEXT NOT NULL,
                success_reason TEXT,
                channel TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL
            )
            """
        )

        connection.commit()


def record_call(
    call_id: str,
    user_id: str,
    outcome: str,
    success_reason: str = "",
    channel: str = "browser",
    started_at: str = "",
    ended_at: str = "",
) -> dict[str, Any]:
    """Record the outcome of a completed Kural call."""

    initialize_analytics_database()

    if outcome not in {"successful", "failed"}:
        outcome = "failed"

    if not started_at:
        started_at = datetime.now(timezone.utc).isoformat()

    if not ended_at:
        ended_at = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO calls (
                call_id,
                user_id,
                outcome,
                success_reason,
                channel,
                started_at,
                ended_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                call_id,
                user_id,
                outcome,
                success_reason,
                channel,
                started_at,
                ended_at,
            ),
        )

        connection.commit()

    return {
        "success": True,
        "call_id": call_id,
        "outcome": outcome,
    }


def get_call_metrics() -> dict[str, int]:
    """Return dashboard metrics."""

    initialize_analytics_database()

    with sqlite3.connect(DATABASE_PATH) as connection:

        total = connection.execute(
            "SELECT COUNT(*) FROM calls"
        ).fetchone()[0]

        successful = connection.execute(
            "SELECT COUNT(*) FROM calls WHERE outcome = 'successful'"
        ).fetchone()[0]

        failed = connection.execute(
            "SELECT COUNT(*) FROM calls WHERE outcome = 'failed'"
        ).fetchone()[0]

    return {
        "total_calls": total,
        "successful_calls": successful,
        "failed_calls": failed,
    }
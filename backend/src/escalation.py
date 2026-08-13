import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATABASE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "kural_escalations.db"
)


def initialize_escalation_database() -> None:
    """Create the escalation database and requests table."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS escalations (
                reference_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                issue_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                what_happened TEXT NOT NULL,
                agent_checked TEXT,
                urgency TEXT NOT NULL,
                language TEXT,
                follow_up_method TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def create_escalation(
    user_id: str,
    issue_type: str,
    summary: str,
    what_happened: str,
    agent_checked: str = "",
    urgency: str = "high",
    language: str = "",
    follow_up_method: str = "",
) -> dict[str, Any]:
    """
    Create a human-help request and return its reference ID.
    """

    initialize_escalation_database()

    reference_id = f"KRL-{uuid.uuid4().hex[:8].upper()}"
    created_at = datetime.now(timezone.utc).isoformat()

    urgency = urgency.lower().strip()

    if urgency not in {"low", "medium", "high", "emergency"}:
        urgency = "high"

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            INSERT INTO escalations (
                reference_id,
                user_id,
                issue_type,
                summary,
                what_happened,
                agent_checked,
                urgency,
                language,
                follow_up_method,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reference_id,
                user_id,
                issue_type,
                summary,
                what_happened,
                agent_checked,
                urgency,
                language,
                follow_up_method,
                "open",
                created_at,
            ),
        )

        connection.commit()

    return {
        "success": True,
        "reference_id": reference_id,
        "status": "open",
        "urgency": urgency,
        "created_at": created_at,
        "message": (
            "Human-help request created successfully."
        ),
    }


def list_escalations() -> list[dict[str, Any]]:
    """Return all human-help requests."""

    initialize_escalation_database()

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT
                reference_id,
                user_id,
                issue_type,
                summary,
                what_happened,
                agent_checked,
                urgency,
                language,
                follow_up_method,
                status,
                created_at
            FROM escalations
            ORDER BY created_at DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]
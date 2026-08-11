import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATABASE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "kural_memory.db"
)


def initialize_database() -> None:
    """Create the Kural memory database and users table if needed."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                language_preference TEXT,
                facts TEXT NOT NULL DEFAULT '{}',
                last_interaction TEXT
            )
            """
        )
        connection.commit()


def lookup_user(user_id: str) -> dict[str, Any]:
    """Return saved memory for a caller, or found=False."""
    initialize_database()

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row

        row = connection.execute(
            """
            SELECT
                user_id,
                name,
                language_preference,
                facts,
                last_interaction
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        return {"found": False}

    try:
        facts = json.loads(row["facts"] or "{}")
    except json.JSONDecodeError:
        facts = {}

    return {
        "found": True,
        "user_id": row["user_id"],
        "name": row["name"],
        "language_preference": row["language_preference"],
        "facts": facts,
        "last_interaction": row["last_interaction"],
    }


def save_user_memory(
    user_id: str,
    name: str | None = None,
    language_preference: str | None = None,
    facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create or update a caller's saved memory."""
    initialize_database()

    existing = lookup_user(user_id)

    if existing["found"]:
        existing_facts = existing.get("facts") or {}

        if facts:
            existing_facts.update(facts)

        final_name = name or existing.get("name")
        final_language = (
            language_preference
            or existing.get("language_preference")
        )
        final_facts = existing_facts
    else:
        final_name = name
        final_language = language_preference
        final_facts = facts or {}

    timestamp = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            INSERT INTO users (
                user_id,
                name,
                language_preference,
                facts,
                last_interaction
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name = excluded.name,
                language_preference = excluded.language_preference,
                facts = excluded.facts,
                last_interaction = excluded.last_interaction
            """,
            (
                user_id,
                final_name,
                final_language,
                json.dumps(final_facts, ensure_ascii=False),
                timestamp,
            ),
        )
        connection.commit()

    return {
        "success": True,
        "user_id": user_id,
        "name": final_name,
        "language_preference": final_language,
        "facts": final_facts,
        "last_interaction": timestamp,
    }
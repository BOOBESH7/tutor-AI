import logging
import json
import os
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent


def _database_path() -> Path:
    configured_path = os.getenv("DATABASE_PATH", "data/edugenie.sqlite3").strip()
    path = Path(configured_path or "data/edugenie.sqlite3")
    return path if path.is_absolute() else BASE_DIR / path


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=10)) as connection:
        connection.row_factory = sqlite3.Row
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    feature TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_history_user_id_id
                ON chat_history (user_id, id DESC)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            yield connection


def initialize_database() -> None:
    with _connection():
        pass


def save_chat_history(*, user_id: str, question: str, answer: str, feature: str = "qa") -> bool:
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        with _connection() as connection:
            connection.execute(
                """
                INSERT INTO chat_history (user_id, question, answer, feature, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, question, answer, feature, timestamp),
            )
        return True
    except (OSError, sqlite3.Error):
        logger.warning("Could not save EduGenie chat history to the local database.", exc_info=True)
        return False


def get_chat_history(user_id: str) -> list[dict[str, str]]:
    with _connection() as connection:
        records = connection.execute(
            """
            SELECT id, user_id, question, answer, feature, timestamp
            FROM chat_history
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 50
            """,
            (user_id,),
        ).fetchall()

    return [
        {
            **{key: str(record[key]) for key in ("user_id", "question", "answer", "feature", "timestamp")},
            "id": str(record["id"]),
        }
        for record in records
    ]


def get_local_chat_messages() -> list[dict[str, str]]:
    with _connection() as connection:
        records = connection.execute(
            """
            SELECT role, content, timestamp
            FROM local_chat_messages
            ORDER BY id
            """
        ).fetchall()
    return [
        {"role": str(record["role"]), "content": str(record["content"]), "time": str(record["timestamp"])}
        for record in records
    ]


def append_local_chat_message(role: str, content: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO local_chat_messages (role, content, timestamp)
            VALUES (?, ?, ?)
            """,
            (role, content, timestamp),
        )


def clear_local_chat_messages() -> None:
    with _connection() as connection:
        connection.execute("DELETE FROM local_chat_messages")


def migrate_legacy_chat_history(messages: list[dict[str, str]]) -> None:
    with _connection() as connection:
        already_migrated = connection.execute(
            "SELECT 1 FROM app_settings WHERE key = ?",
            ("legacy_chat_history_migrated",),
        ).fetchone()
        if already_migrated:
            return

        for message in messages:
            role = message.get("role")
            content = message.get("content")
            if (
                not isinstance(role, str)
                or role not in {"user", "assistant"}
                or not isinstance(content, str)
            ):
                raise ValueError("The existing chat history file contains an invalid message.")
            timestamp = message.get("time", "")
            if not isinstance(timestamp, str):
                raise ValueError("The existing chat history file contains an invalid timestamp.")
            timestamp = timestamp or datetime.now(timezone.utc).isoformat()
            connection.execute(
                """
                INSERT INTO local_chat_messages (role, content, timestamp)
                VALUES (?, ?, ?)
                """,
                (role, content, timestamp),
            )
        connection.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?)",
            ("legacy_chat_history_migrated", "1"),
        )


def migrate_legacy_chat_history_file(path: Path) -> None:
    if not path.exists():
        migrate_legacy_chat_history([])
        return

    messages = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(messages, list) or any(not isinstance(message, dict) for message in messages):
        raise ValueError("The existing chat history file is not a list of messages.")
    migrate_legacy_chat_history(messages)

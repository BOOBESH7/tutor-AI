import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from database import (
    append_local_chat_message,
    clear_local_chat_messages,
    get_chat_history,
    get_local_chat_messages,
    initialize_database,
    migrate_legacy_chat_history,
    migrate_legacy_chat_history_file,
    save_chat_history,
    _database_path,
)


class ChatHistoryDatabaseTests(unittest.TestCase):
    def test_vercel_uses_writable_temporary_database_path_by_default(self) -> None:
        with patch.dict(os.environ, {"VERCEL": "1"}, clear=True):
            self.assertEqual(_database_path(), Path(tempfile.gettempdir()) / "edugenie.sqlite3")

    def test_configured_database_path_overrides_vercel_temporary_default(self) -> None:
        configured_path = Path(tempfile.gettempdir()) / "custom-history.sqlite3"
        with patch.dict(
            os.environ,
            {"VERCEL": "1", "DATABASE_PATH": str(configured_path)},
            clear=True,
        ):
            self.assertEqual(_database_path(), configured_path)

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "data" / "history.sqlite3"
        self.environment = patch.dict(os.environ, {"DATABASE_PATH": str(self.database_path)})
        self.environment.start()
        initialize_database()

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary_directory.cleanup()

    def test_history_is_persistent_and_isolated_by_user(self) -> None:
        self.assertTrue(save_chat_history(user_id="student-a", question="Q1", answer="A1"))
        self.assertTrue(save_chat_history(user_id="student-b", question="Other", answer="Private"))
        self.assertTrue(save_chat_history(user_id="student-a", question="Q2", answer="A2", feature="qa"))

        history = get_chat_history("student-a")
        self.assertEqual([entry["question"] for entry in history], ["Q2", "Q1"])
        self.assertEqual(get_chat_history("student-b")[0]["answer"], "Private")
        self.assertEqual([entry["feature"] for entry in history], ["qa", "qa"])
        self.assertTrue(all(datetime.fromisoformat(entry["timestamp"]).tzinfo for entry in history))
        self.assertTrue(all(entry["id"].isdigit() for entry in history))

    def test_history_is_limited_to_newest_fifty_records(self) -> None:
        for index in range(55):
            self.assertTrue(save_chat_history(user_id="student-a", question=f"Q{index}", answer=f"A{index}"))

        history = get_chat_history("student-a")
        self.assertEqual(len(history), 50)
        self.assertEqual(history[0]["question"], "Q54")
        self.assertEqual(history[-1]["question"], "Q5")

    def test_streamlit_messages_use_sqlite_and_can_be_cleared(self) -> None:
        append_local_chat_message("user", "Hello")
        append_local_chat_message("assistant", "Welcome")

        self.assertEqual(
            [(message["role"], message["content"]) for message in get_local_chat_messages()],
            [("user", "Hello"), ("assistant", "Welcome")],
        )

        clear_local_chat_messages()
        self.assertEqual(get_local_chat_messages(), [])

    def test_legacy_chat_history_is_imported_once(self) -> None:
        original_messages = [{"role": "user", "content": "Old message", "time": "2026-01-01T00:00:00+00:00"}]
        migrate_legacy_chat_history(original_messages)
        migrate_legacy_chat_history([{"role": "user", "content": "Duplicate"}])

        self.assertEqual(
            get_local_chat_messages(),
            [{"role": "user", "content": "Old message", "time": "2026-01-01T00:00:00+00:00"}],
        )

    def test_legacy_chat_history_file_is_migrated_without_being_deleted(self) -> None:
        legacy_file = Path(self.temporary_directory.name) / "legacy.json"
        legacy_file.write_text(
            '[{"role":"assistant","content":"Saved answer","time":"2026-01-02T00:00:00+00:00"}]',
            encoding="utf-8",
        )

        migrate_legacy_chat_history_file(legacy_file)

        self.assertTrue(legacy_file.exists())
        self.assertEqual(get_local_chat_messages()[0]["content"], "Saved answer")


if __name__ == "__main__":
    unittest.main()

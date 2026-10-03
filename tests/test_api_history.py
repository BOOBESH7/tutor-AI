import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from database import save_chat_history


class ChatHistoryApiTests(unittest.TestCase):
    def test_history_endpoint_reads_from_local_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "history.sqlite3"
            with patch.dict(os.environ, {"DATABASE_PATH": str(database_path)}):
                previous_overrides = main.app.dependency_overrides.copy()
                main.app.dependency_overrides[main.require_user] = lambda: {"uid": "local-student"}
                try:
                    with TestClient(main.app) as client:
                        empty_response = client.get("/api/history")
                        self.assertEqual(empty_response.status_code, 200)
                        self.assertEqual(empty_response.json(), {"history": []})

                        self.assertTrue(
                            save_chat_history(
                                user_id="local-student",
                                question="What is SQLite?",
                                answer="A local database.",
                            )
                        )
                        history_response = client.get("/api/history")
                        self.assertEqual(history_response.status_code, 200)
                        self.assertEqual(
                            history_response.json()["history"][0]["question"],
                            "What is SQLite?",
                        )
                finally:
                    main.app.dependency_overrides = previous_overrides

    def test_learning_plan_endpoint_generates_a_custom_topic_roadmap(self) -> None:
        expected_plan = {
            "beginner": {"topics": ["HTML"], "explanation": "Learn the basics."},
            "intermediate": {"topics": ["CSS"]},
            "advanced": {"topics": ["JavaScript"]},
        }
        previous_overrides = main.app.dependency_overrides.copy()
        main.app.dependency_overrides[main.require_user] = lambda: {"uid": "local-student"}
        try:
            with patch("main.recommend_learning_path", return_value=expected_plan) as generate_plan:
                with TestClient(main.app) as client:
                    response = client.post(
                        "/learn/recommendations",
                        json={
                            "topic": "Web development",
                            "goal": "Build a portfolio website",
                            "level": "Beginner",
                        },
                    )
        finally:
            main.app.dependency_overrides = previous_overrides

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["learning_path"], expected_plan)
        self.assertEqual(response.json()["topic"], "Web development")
        generate_plan.assert_called_once_with(
            "Web development", "Build a portfolio website", "Beginner"
        )


if __name__ == "__main__":
    unittest.main()

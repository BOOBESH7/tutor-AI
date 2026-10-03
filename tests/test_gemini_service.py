import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from gemini_service import generate_text


class GeminiServiceTests(unittest.TestCase):
    def test_default_model_is_used_when_no_model_is_configured(self) -> None:
        response = SimpleNamespace(text="OK")
        generate_content = Mock(return_value=response)
        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))

        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True),
            patch("gemini_service._client", return_value=client),
        ):
            self.assertEqual(generate_text("Reply OK"), "OK")

        self.assertEqual(generate_content.call_args.kwargs["model"], "gemini-3.1-flash-lite")

    def test_configured_model_is_passed_to_gemini(self) -> None:
        response = SimpleNamespace(text="OK")
        generate_content = Mock(return_value=response)
        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))

        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False),
            patch.dict(os.environ, {"GEMINI_MODEL": "gemini-3.8-flash"}),
            patch("gemini_service._client", return_value=client),
        ):
            self.assertEqual(generate_text("Reply OK"), "OK")

        self.assertEqual(generate_content.call_args.kwargs["model"], "gemini-3.8-flash")


if __name__ == "__main__":
    unittest.main()

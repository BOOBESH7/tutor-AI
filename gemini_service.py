import os
from functools import lru_cache

from google import genai


class GeminiServiceError(Exception):
    """A safe-to-display Gemini configuration or service failure."""


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if api_key and api_key != "YOUR_GEMINI_API_KEY":
        try:
            return genai.Client(api_key=api_key)
        except Exception as exc:
            raise GeminiServiceError("Gemini could not be initialized. Check the API key configuration.") from exc

    raise GeminiServiceError("Gemini is not configured. Add your GEMINI_API_KEY to the .env file.")


def generate_text(prompt: str, *, json_response: bool = False) -> str:
    try:
        from google.genai import types

        config = types.GenerateContentConfig(
            response_mime_type="application/json" if json_response else "text/plain"
        )
        response = _client().models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
            contents=prompt,
            config=config,
        )
        text = getattr(response, "text", None)
        if not text or not text.strip():
            raise GeminiServiceError("Gemini returned an empty response. Please try again.")
        return text.strip()
    except GeminiServiceError:
        raise
    except Exception as exc:
        raise GeminiServiceError(
            "Gemini could not complete that request. Check your API key, quota, and network connection, then try again."
        ) from exc

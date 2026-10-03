import json
import re
from typing import Any

from gemini_service import generate_text


def _parse_json(text: str) -> Any:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    return json.loads(cleaned)


def generate_quiz(text: str, subject: str = "", level: str = "Beginner") -> list[dict[str, Any]]:
    prompt = (
        "Create exactly 3 educational multiple-choice questions using the source text. "
        "Return a JSON array only. Every array item must have: question (string), options (object with exactly "
        "keys A, B, C, D and string values), correct_answer (one letter A/B/C/D), and explanation (short string). "
        "Distractors should be plausible and the answer must be supported by the source.\n"
        f"Subject: {subject or 'general'}; learner level: {level}.\nSource text:\n{text}"
    )
    result = _parse_json(generate_text(prompt, json_response=True))
    if isinstance(result, dict):
        result = result.get("questions")
    if not isinstance(result, list) or len(result) != 3:
        raise ValueError("Gemini did not return exactly three quiz questions.")

    validated = []
    for item in result:
        if not isinstance(item, dict):
            raise ValueError("Gemini returned an invalid quiz question.")
        options = item.get("options")
        correct = str(item.get("correct_answer", "")).strip().upper()
        if not isinstance(options, dict) or any(key not in options for key in "ABCD") or correct not in "ABCD":
            raise ValueError("Gemini returned an invalid quiz answer or options.")
        validated.append({
            "question": str(item.get("question", "")),
            "options": {key: str(options[key]) for key in "ABCD"},
            "correct_answer": correct,
            "explanation": str(item.get("explanation", "")),
        })
        if not validated[-1]["question"]:
            raise ValueError("Gemini returned an empty quiz question.")
    return validated

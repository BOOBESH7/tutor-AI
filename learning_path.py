import json

from gemini_service import generate_text


def recommend_learning_path(topic: str, goal: str = "", level: str = "") -> dict:
    prompt = (
        "Create a practical learning path for the given topic, progressing from beginner to intermediate to advanced. "
        "Return one valid JSON object with keys beginner, intermediate, advanced. Each stage must contain topics (array of strings), "
        "explanation (string), learning_order (array of strings), practice (array of strings), and resources (array of strings). "
        "Recommend reputable resource names or URLs; do not invent specific courses. Keep every item concise and clear, "
        "and do not use Markdown markers, decorative symbols, or emojis inside JSON values.\n"
        f"Topic: {topic}\nLearner's current level: {level or 'not specified'}\nLearning goal: {goal or 'general understanding'}"
    )
    result = json.loads(generate_text(prompt, json_response=True))
    stages = ("beginner", "intermediate", "advanced")
    if not isinstance(result, dict) or any(stage not in result or not isinstance(result[stage], dict) for stage in stages):
        raise ValueError("Gemini returned an invalid learning path.")
    return result

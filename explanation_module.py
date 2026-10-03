from gemini_service import generate_text


def explain_topic(topic: str) -> str:
    prompt = (
        "Explain this topic to a beginner with little technical background. Use these sections where appropriate: "
        "Simple definition, How it works, Example, Key points, Short summary. Keep the language clear and approachable. "
        "Use clean Markdown headings and bullets only when useful; do not include decorative symbols or unnecessary emojis.\n"
        f"Topic: {topic}"
    )
    return generate_text(prompt)

from gemini_service import generate_text


def summarize_text(text: str) -> str:
    prompt = (
        "Summarize the educational text concisely in simple language. Preserve all important information, "
        "remove repetition, and do not change the meaning. Use clean Markdown bullets or short headings only when useful. "
        "Do not add decorative symbols, emojis, or information not present in the source.\n"
        f"Text:\n{text}"
    )
    return generate_text(prompt)

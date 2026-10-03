from gemini_service import generate_text


def answer_question(question: str, subject: str = "", level: str = "Beginner", age_group: str = "student") -> str:
    prompt = (
        "You are EduGenie, a careful academic tutor. Answer accurately in simple English, "
        "explain difficult terms, and keep the answer concise but useful (usually under 200 words). Answer the question directly. "
        "Use clean Markdown only when it improves readability: short headings, simple bullets, and bold key terms. "
        "Do not use decorative symbols, repeated punctuation, or unnecessary emojis. "
        "Use a small example when it makes the idea clearer.\n"
        f"Learner: {age_group}; subject: {subject or 'general'}; level: {level}.\n"
        f"Question: {question}"
    )
    return generate_text(prompt)

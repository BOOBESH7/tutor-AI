import json
import os
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from database import (
    append_local_chat_message,
    clear_local_chat_messages,
    get_local_chat_messages,
    migrate_legacy_chat_history_file,
)

load_dotenv()

HISTORY_FILE = Path(__file__).with_name("chat_history.json")
MODEL_NAME = "gpt-4o-mini"

COURSE_CATALOG = [
    {
        "title": "Python for Engineering",
        "level": "Beginner to Advanced",
        "duration": "6 weeks",
        "description": "Master Python fundamentals, object-oriented programming, automation, and coding logic for core engineering tasks.",
        "tags": ["Python", "Automation", "OOP"],
    },
    {
        "title": "Data Structures & Algorithms",
        "level": "Intermediate",
        "duration": "8 weeks",
        "description": "Learn arrays, stacks, trees, graphs, recursion, and optimization strategies used in interviews and real projects.",
        "tags": ["DSA", "Problem Solving", "Interview Prep"],
    },
    {
        "title": "Java & Core Concepts",
        "level": "Intermediate",
        "duration": "7 weeks",
        "description": "Build strong Java foundations including classes, inheritance, collections, exception handling, and backend logic.",
        "tags": ["Java", "OOP", "Backend"],
    },
    {
        "title": "DBMS & SQL",
        "level": "Intermediate",
        "duration": "5 weeks",
        "description": "Understand database design, normalization, schema modeling, queries, and data integrity in real systems.",
        "tags": ["SQL", "DBMS", "Data"],
    },
    {
        "title": "Operating Systems",
        "level": "Advanced",
        "duration": "4 weeks",
        "description": "Explore process management, memory allocation, scheduling, concurrency, and system resource handling.",
        "tags": ["OS", "Systems", "Architecture"],
    },
    {
        "title": "Computer Networks",
        "level": "Intermediate",
        "duration": "4 weeks",
        "description": "Study TCP/IP, routing, networking protocols, debugging, and communication between distributed systems.",
        "tags": ["Networking", "Protocols", "Security"],
    },
]

ROADMAPS = [
    {
        "title": "Full-Stack Developer Roadmap",
        "timeline": "12 weeks",
        "outcomes": ["HTML/CSS/JS", "Python/Flask", "Database design", "Deployment"],
    },
    {
        "title": "DSA Mastery Path",
        "timeline": "10 weeks",
        "outcomes": ["Arrays", "Linked Lists", "Trees", "Graphs", "Interview drills"],
    },
    {
        "title": "AI & Cloud Learning Track",
        "timeline": "8 weeks",
        "outcomes": ["Generative AI", "Prompt engineering", "Cloud basics", "Real apps"],
    },
]

st.set_page_config(page_title="EduGenie", page_icon="🎓", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background:
            radial-gradient(circle at top left, rgba(124, 58, 237, 0.30), transparent 24%),
            radial-gradient(circle at top right, rgba(59, 130, 246, 0.18), transparent 28%),
            radial-gradient(circle at bottom left, rgba(45, 212, 191, 0.10), transparent 25%),
            linear-gradient(135deg, #050b14 0%, #0b1220 25%, #101b2f 100%);
        color: #edf5ff;
    }

    [data-testid="stSidebar"] {
        background: rgba(8, 12, 20, 0.92);
        border-right: 1px solid rgba(148, 163, 184, 0.14);
    }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2.5rem;
        max-width: 1420px;
    }

    h1, h2, h3, h4 {
        letter-spacing: -0.04em;
        color: #f8fbff !important;
    }

    p, li, div, span {
        color: #dfeafc;
    }

    .stButton > button {
        background: linear-gradient(135deg, #7c3aed 0%, #3b82f6 100%);
        border: none;
        border-radius: 14px;
        color: white;
        font-weight: 700;
        padding: 0.75rem 1.1rem;
        box-shadow: 0 16px 30px rgba(90, 109, 255, 0.28);
    }

    .stRadio > div {
        gap: 0.5rem;
        flex-wrap: wrap;
    }

    [role="radiogroup"] label {
        background: rgba(15, 23, 36, 0.65);
        border: 1px solid rgba(148, 163, 184, 0.12);
        border-radius: 12px;
        padding: 0.5rem 0.8rem;
        margin-right: 0.5rem;
    }

    .stChatMessage {
        background: linear-gradient(180deg, rgba(19, 28, 42, 0.95), rgba(15, 22, 34, 0.8));
        border: 1px solid rgba(167, 177, 255, 0.18);
        border-radius: 18px;
        padding: 1rem 1.1rem;
        box-shadow: 0 16px 32px rgba(3, 7, 18, 0.26);
    }

    [data-testid="stChatInput"] {
        background: rgba(11, 17, 27, 0.9);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 18px;
        box-shadow: 0 18px 36px rgba(3, 7, 18, 0.28);
        padding: 0.8rem;
    }

    .stChatInput textarea {
        background: transparent !important;
        color: white !important;
        font-size: 1rem !important;
        min-height: 62px !important;
    }

    .glass-panel {
        background: linear-gradient(180deg, rgba(13, 20, 32, 0.84), rgba(11, 17, 27, 0.78));
        border: 1px solid rgba(148, 163, 184, 0.14);
        border-radius: 24px;
        padding: 1.2rem 1.35rem;
        box-shadow: 0 18px 42px rgba(3, 7, 18, 0.26);
        backdrop-filter: blur(10px);
    }

    .premium-hero {
        position: relative;
        background: linear-gradient(135deg, rgba(124, 58, 237, 0.20), rgba(59, 130, 246, 0.14), rgba(16, 185, 129, 0.10));
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 30px;
        padding: 1.5rem 1.5rem 1.2rem;
        box-shadow: 0 22px 44px rgba(3, 7, 18, 0.28);
        overflow: hidden;
    }

    .premium-hero::before {
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(120deg, transparent 0%, rgba(255,255,255,0.07) 45%, transparent 100%);
        pointer-events: none;
    }

    .gemini-badge {
        display: inline-block;
        margin-bottom: 0.8rem;
        border-radius: 999px;
        background: linear-gradient(135deg, rgba(59,130,246,0.18), rgba(168,85,247,0.18));
        border: 1px solid rgba(147,197,253,0.25);
        color: #dfeaff;
        padding: 0.38rem 0.85rem;
        font-size: 0.72rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-weight: 700;
    }

    .nav-chip {
        display: inline-block;
        margin: 0 0.5rem 0.55rem 0;
        padding: 0.42rem 0.75rem;
        border-radius: 999px;
        background: rgba(15, 23, 42, 0.70);
        border: 1px solid rgba(148, 163, 184, 0.18);
        color: #dfeaff;
        font-size: 0.72rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        font-weight: 600;
    }

    .metric-card {
        background: linear-gradient(180deg, rgba(20, 30, 47, 0.96), rgba(11, 18, 29, 0.9));
        border: 1px solid rgba(93, 156, 255, 0.18);
        border-radius: 20px;
        padding: 1rem 1.1rem;
        min-height: 120px;
        box-shadow: 0 15px 34px rgba(7, 11, 20, 0.25);
    }

    .metric-card h3 {
        margin-bottom: 0.7rem;
        font-size: 0.74rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #9cc8ff !important;
    }

    .metric-card .value {
        margin: 0;
        font-size: 1.75rem;
        font-weight: 800;
        color: #f4f8ff;
    }

    .status-box {
        background: linear-gradient(180deg, rgba(11, 16, 25, 0.92), rgba(13, 19, 30, 0.8));
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-radius: 22px;
        padding: 1rem 1.1rem;
        box-shadow: 0 18px 34px rgba(4, 7, 18, 0.2);
    }

    .status-box .label {
        color: #9cc8ff;
        font-size: 0.72rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.45rem;
    }

    .status-box .value {
        color: #f4f8ff;
        font-size: 1.8rem;
        font-weight: 800;
        margin: 0;
    }

    .feature-card {
        background: linear-gradient(180deg, rgba(11, 16, 25, 0.88), rgba(13, 19, 30, 0.76));
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 22px;
        padding: 1rem 1rem 1.1rem;
        height: 100%;
        box-shadow: 0 18px 34px rgba(4, 7, 18, 0.18);
    }

    .feature-card h4 {
        margin-top: 0.5rem;
        margin-bottom: 0.4rem;
    }

    .feature-card .tag {
        display: inline-block;
        padding: 0.3rem 0.7rem;
        background: rgba(96, 165, 250, 0.12);
        border: 1px solid rgba(147, 197, 253, 0.20);
        border-radius: 999px;
        color: #dbeafe;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }

    .course-card {
        background: linear-gradient(180deg, rgba(13, 20, 32, 0.9), rgba(11, 17, 27, 0.75));
        border: 1px solid rgba(148, 163, 184, 0.14);
        border-radius: 22px;
        padding: 1rem 1rem 1.15rem;
        height: 100%;
        box-shadow: 0 18px 34px rgba(4, 7, 18, 0.18);
    }

    .course-card h4 {
        margin-top: 0.7rem;
        margin-bottom: 0.4rem;
    }

    .course-card .meta {
        font-size: 0.74rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #9cc8ff;
        margin-bottom: 0.6rem;
    }

    .roadmap-card {
        background: linear-gradient(180deg, rgba(12, 18, 30, 0.9), rgba(10, 14, 22, 0.8));
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 22px;
        padding: 1rem 1rem 1.15rem;
        height: 100%;
    }

    .roadmap-card li {
        margin-bottom: 0.4rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_chat_history() -> list[dict[str, str]]:
    migrate_legacy_chat_history_file(HISTORY_FILE)
    return get_local_chat_messages()


def append_chat_message(role: str, content: str) -> None:
    st.session_state.chat_history.append({"role": role, "content": content})
    append_local_chat_message(role, content)


def init_session_state() -> None:
    defaults = {
        "chat_history": load_chat_history(),
        "quiz_questions": [],
        "quiz_index": 0,
        "quiz_score": 0,
        "last_topic": "Programming",
        "progress": {},
        "api_ready": False,
        "last_voice_capture": "",
        "active_tab": "Home",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def configure_model() -> Any:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    client = OpenAI(api_key=api_key)
    st.session_state.api_ready = True
    return client


def generate_demo_learning_response(user_message: str, subject: str, level: str, age_group: str) -> str:
    topic = extract_topic(subject, user_message)
    text = user_message.strip()
    answer = f"""
Here is a structured answer for your question on {subject}.

1. Core idea: {topic} is a key concept in {subject}. The main goal is to understand the principle before trying to memorize a formula or shortcut.
2. Why it matters: In engineering and computer science, understanding the concept helps you solve new problems, write cleaner code, and explain your reasoning in exams and interviews.
3. Step-by-step reasoning: start by identifying the problem, recall the rule or pattern involved, test it on a simple example, and then apply it to the full scenario.
4. Example: if you are learning {topic}, think of a small real-world case first. Then connect that case to the concept and check whether your logic matches the expected result.
5. Study tip: revise the definition, solve 2 small practice questions, and summarize the concept in your own words before moving to the next topic.

You can ask follow-up questions like: 'Explain this with an example', 'Give me a practice question', or 'Explain the difference between theory and application'.
"""
    if "python" in text.lower() or "java" in text.lower() or "dsa" in text.lower():
        answer = f"""
For {subject}, the best way to learn is to focus on understanding patterns instead of memorizing answers.

- First, identify the problem type.
- Second, choose the right concept or data structure.
- Third, test with a simple example.
- Fourth, check edge cases and time complexity.

Example for {topic}: break the problem into smaller parts, write the logic in simple steps, then convert it into code or pseudocode. This is how strong engineering students approach programming and algorithm questions.

Quick study strategy:
1. Learn the definition.
2. Understand the flow with one example.
3. Solve a mini problem.
4. Review mistakes and re-explain the idea in your own words.
"""
    return answer.strip()


def generate_demo_quiz(subject: str, topic: str, level: str) -> list[dict[str, Any]]:
    return [
        {
            "question": f"What is the most important step when learning {topic} in {subject}?",
            "options": ["Understand the concept first", "Memorize without practice", "Skip examples", "Guess the answer"],
            "correct_answer": "Understand the concept first",
            "explanation": "A strong learner understands the concept first and then practices with examples to build real confidence.",
        },
        {
            "question": f"Which method is best to improve your understanding of {topic}?",
            "options": ["Practice with small examples", "Ignore the fundamentals", "Repeat random notes", "Avoid solving problems"],
            "correct_answer": "Practice with small examples",
            "explanation": "Small practice examples turn theory into real understanding and improve retention.",
        },
        {
            "question": f"Why is reviewing mistakes useful in {subject}?",
            "options": ["It helps identify weak points and improve learning", "It makes learning slower", "It removes all challenge", "It avoids practice"],
            "correct_answer": "It helps identify weak points and improve learning",
            "explanation": "Reviewing mistakes is one of the most effective ways to improve understanding and performance.",
        },
        {
            "question": f"What is a good next step after learning {topic}?",
            "options": ["Solve a related question", "Stop studying", "Memorize only", "Skip implementation"],
            "correct_answer": "Solve a related question",
            "explanation": "Applying the idea to a related question confirms whether the concept is truly understood.",
        },
    ]


def extract_topic(subject: str, text: str) -> str:
    if text:
        words = text.strip().split()
        if len(words) > 3:
            return " ".join(words[:5])
    return subject


def build_system_prompt(subject: str, level: str, age_group: str) -> str:
    return f"""
You are EduGenie, an expert academic tutor for engineering college students.

Mission:
- Teach with a professional, supportive, and intellectually rigorous tone.
- Explain concepts clearly, with logic first and examples second.
- Adapt to the student level: {level}, age group: {age_group}, and primary subject: {subject}.
- Focus on understanding, problem-solving, and confidence-building for real academic growth.

Core responsibilities:
- Explain technical topics such as Python, Java, DSA, DBMS, OS, networking, web development, and engineering fundamentals.
- Break complex concepts into structured steps.
- Offer guided reasoning before direct answers.
- Suggest study strategies and learning resources.
- Generate practice questions and concept checks when needed.

Guidelines:
- Encourage academic integrity and honest learning.
- If uncertain, say so and recommend reliable references.
- Keep explanations concise but deep enough for real academic value.
"""


def format_history() -> str:
    history = st.session_state.get("chat_history", [])
    if not history:
        return "No prior conversation."

    parts = []
    for message in history[-8:]:
        speaker = "Student" if message["role"] == "user" else "Tutor"
        parts.append(f"{speaker}: {message['content']}")
    return "\n".join(parts)


def generate_learning_response(user_message: str, subject: str, level: str, age_group: str, model: Any) -> str:
    prompt = f"""
{build_system_prompt(subject, level, age_group)}

Subject: {subject}
Level: {level}
Age group: {age_group}
Student question: {user_message}

Conversation history:
{format_history()}

Respond like a professional engineering mentor and study coach. Provide:
1. A clear explanation of the concept.
2. A small example or analogy.
3. A concise next step or practice question.
4. A hint before a full solution when the topic is technical.
"""
    try:
        response = model.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": build_system_prompt(subject, level, age_group)},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=700,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return (
            "The AI service is temporarily unavailable right now. Please try again in a few moments. "
            "Meanwhile, I can still help with concept breakdowns, practice questions, and study guidance."
        )


def generate_quiz(subject: str, topic: str, level: str, model: Any) -> list[dict[str, Any]]:
    quiz_prompt = f"""
Create a 4-question multiple-choice quiz about {topic} in {subject}. The learner's level is {level}.
Return valid JSON only in this format:
[
  {{
    "question": "...",
    "options": ["A", "B", "C", "D"],
    "correct_answer": "A",
    "explanation": "Why this answer is correct"
  }}
]
No markdown fences and no extra text.
"""

    try:
        result = model.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": quiz_prompt}],
            temperature=0.6,
            max_tokens=1000,
        )
        raw_text = result.choices[0].message.content.strip()
        if "```" in raw_text:
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_text)
    except Exception:
        return [
            {
                "question": f"What is the core idea behind {topic}?",
                "options": ["A key concept", "A random guess", "A missing fact", "A shortcut"],
                "correct_answer": "A key concept",
                "explanation": "The correct answer reflects the main concept students need to understand before solving practical tasks.",
            },
            {
                "question": f"Which method best supports learning {topic}?",
                "options": ["Practice and reasoning", "Memorizing without understanding", "Skipping examples", "Guessing the answer"],
                "correct_answer": "Practice and reasoning",
                "explanation": "Strong conceptual learning comes from repeated practice and reasoning, not memorization alone.",
            },
            {
                "question": f"Why is it important to understand {topic}?",
                "options": ["It builds deeper engineering knowledge", "It makes learning unnecessary", "It removes all challenge", "It eliminates problem solving"],
                "correct_answer": "It builds deeper engineering knowledge",
                "explanation": "Understanding the concept helps apply the idea in real projects, exams, and interviews.",
            },
            {
                "question": f"What is the best next step after learning {topic}?",
                "options": ["Solve a related problem", "Stop studying", "Avoid examples", "Memorize only"],
                "correct_answer": "Solve a related problem",
                "explanation": "Applying the concept in a related problem confirms real understanding and retention.",
            },
        ]


def track_progress(subject: str, topic: str) -> None:
    current = st.session_state.progress
    subject_stats = current.setdefault(subject, {"count": 0, "topics": []})
    subject_stats["count"] += 1
    if topic not in subject_stats["topics"]:
        subject_stats["topics"].append(topic)
    st.session_state.last_topic = topic


def render_chat_history() -> None:
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                content = message["content"]
                st.markdown(content)
                speak_script = (
                    "const text = "
                    + json.dumps(content)
                    + "; if ('speechSynthesis' in window) { const utterance = new SpeechSynthesisUtterance(text); utterance.lang = 'en-US'; utterance.rate = 1; window.speechSynthesis.cancel(); window.speechSynthesis.speak(utterance); } else { alert('Speech synthesis is not supported in this browser.'); }"
                )
                st.markdown(
                    f"""
                    <div style="display:flex; justify-content:flex-end; margin-top: .55rem;">
                        <button onclick="{speak_script}">🔊 Listen</button>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(message["content"])


def voice_input_component() -> str:
    component_value = st.components.v1.html(
        """
        <div style="padding: 0.8rem; border-radius: 16px; background: rgba(15, 23, 36, 0.82); border: 1px solid rgba(148, 163, 184, 0.2); box-shadow: 0 14px 28px rgba(3,7,18,0.2);">
            <textarea id="edu-voice-text" rows="3" placeholder="Speak your question here..." style="width:100%; resize:vertical; background: rgba(15,23,36,0.82); color:#edf4ff; border: 1px solid rgba(148,163,184,0.2); border-radius: 12px; padding: 0.8rem; font-size: 0.96rem;"></textarea>
            <div style="display:flex; gap: 0.6rem; margin-top: 0.75rem; flex-wrap: wrap;">
                <button id="edu-voice-btn" type="button" style="background: linear-gradient(135deg, #7c3aed 0%, #3b82f6 100%); color: white; border: none; border-radius: 12px; padding: 0.7rem 1rem; font-weight: 700; cursor: pointer;">🎙️ Speak</button>
                <button id="edu-send-btn" type="button" style="background: rgba(30, 41, 59, 0.9); color: white; border: 1px solid rgba(148, 163, 184, 0.25); border-radius: 12px; padding: 0.7rem 1rem; font-weight: 700; cursor: pointer;">Use voice text</button>
            </div>
        </div>
        <script>
            const textarea = document.getElementById('edu-voice-text');
            const voiceBtn = document.getElementById('edu-voice-btn');
            const sendBtn = document.getElementById('edu-send-btn');
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

            const sendValue = () => {
                const text = (textarea.value || '').trim();
                if (text) {
                    window.parent.postMessage({ type: 'streamlit:setComponentValue', value: text }, '*');
                }
            };

            if (SpeechRecognition) {
                const recognition = new SpeechRecognition();
                recognition.lang = 'en-US';
                recognition.interimResults = false;
                recognition.continuous = false;

                voiceBtn.addEventListener('click', () => {
                    textarea.value = 'Listening...';
                    recognition.start();
                });

                recognition.onresult = (event) => {
                    let transcript = '';
                    for (let i = 0; i < event.results.length; i++) {
                        transcript += event.results[i][0].transcript;
                    }
                    textarea.value = transcript.trim();
                };

                recognition.onerror = () => {
                    textarea.value = 'Voice recognition failed. Please type your message or try again.';
                };
            } else {
                voiceBtn.addEventListener('click', () => {
                    textarea.value = 'Speech recognition is not supported in this browser. Please type your question.';
                });
            }

            sendBtn.addEventListener('click', sendValue);
        </script>
        """,
        height=190,
    )
    return component_value if isinstance(component_value, str) else ""


def process_chat_prompt(prompt: str, subject: str, level: str, age_group: str, model: Any) -> None:
    user_message = prompt.strip()
    if not user_message:
        return

    if user_message.lower().startswith("quiz"):
        if model is None:
            generated = generate_demo_quiz(subject, st.session_state.last_topic, level)
        else:
            generated = generate_quiz(subject, st.session_state.last_topic, level, model)
        st.session_state.quiz_questions = generated
        st.session_state.quiz_index = 0
        st.session_state.quiz_score = 0
        append_chat_message("user", user_message)
        append_chat_message("assistant", "I created a quiz for you. Answer the questions below and I will explain each result.")
        return

    append_chat_message("user", user_message)
    topic = extract_topic(subject, user_message)
    track_progress(subject, topic)
    if model is None:
        response = generate_demo_learning_response(user_message, subject, level, age_group)
    else:
        response = generate_learning_response(user_message, subject, level, age_group, model)
    append_chat_message("assistant", response)


def render_quiz() -> None:
    if not st.session_state.quiz_questions:
        return

    questions = st.session_state.quiz_questions
    index = st.session_state.quiz_index
    total = len(questions)

    if index >= total:
        st.success(f"Quiz finished! Your score: {st.session_state.quiz_score}/{total}")
        with st.expander("View study tips"):
            st.write("Review the explanations, revisit the topic in simpler terms, and try a quick problem before moving ahead.")
        return

    current = questions[index]
    with st.container():
        st.subheader(f"Question {index + 1} of {total}")
        st.write(current["question"])
        choice = st.radio("Select an answer", current["options"], key=f"quiz_choice_{index}")

        if st.button("Submit answer", key=f"submit_{index}"):
            is_correct = choice == current["correct_answer"]
            if is_correct:
                st.session_state.quiz_score += 1
                st.success(f"Correct! {current['explanation']}")
            else:
                st.error(f"Not quite. The correct answer is {current['correct_answer']}. {current['explanation']}")
            st.session_state.quiz_index += 1
            st.rerun()


def render_home() -> None:
    st.markdown(
        """
        <div class="premium-hero">
            <div class="gemini-badge">Gemini AI Learning</div>
            <div style="display:flex; flex-wrap:wrap; margin-bottom: 0.8rem;">
                <span class="nav-chip">AI tutor</span>
                <span class="nav-chip">Engineering</span>
                <span class="nav-chip">Deep learning</span>
                <span class="nav-chip">Career growth</span>
            </div>
            <h1 style="margin-bottom: 0.35rem; font-size: 2.6rem;">EduGenie</h1>
            <p style="margin:0; color:#deebff; font-size:1.08rem; max-width:960px;">
                A premium study platform for engineering college students, designed to help learners with concept clarity,
                coding practice, roadmap planning, and AI-powered academic guidance.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    top_cols = st.columns([2, 1])
    with top_cols[0]:
        st.markdown(
            """
            <div class="glass-panel" style="margin-top: 1rem;">
                <div style="font-size:0.74rem; letter-spacing:0.08em; text-transform:uppercase; color:#9cc8ff; margin-bottom:0.65rem;">Platform advantages</div>
                <ul style="margin:0; padding-left:1.1rem; line-height:1.8;">
                    <li>Structured explanation for Python, Java, DSA, DBMS, OS, and networking</li>
                    <li>Adaptive quiz generation with instant feedback and learning corrections</li>
                    <li>Weekly learning roadmaps for skill-building and placement readiness</li>
                    <li>AI study guidance that supports learning rather than shortcuts</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top_cols[1]:
        st.markdown(
            """
            <div class="status-box" style="margin-top:1rem;">
                <div class="label">Learning system</div>
                <p class="value">Live</p>
                <div style="margin-top: 0.8rem; color: #dfe9ff; font-size: 0.95rem;">Student success dashboard</div>
                <div style="margin-top: 0.4rem; color: #8fe7c8; font-weight:700;">Ready for engineering study</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    metric_cols = st.columns(3)
    for i, item in enumerate([
        ("AI Mentor", "Adaptive"),
        ("Study Tracks", "6+"),
        ("Career Focus", "Placement"),
    ]):
        with metric_cols[i]:
            st.markdown(
                f"""
                <div class="metric-card">
                    <h3>{item[0]}</h3>
                    <p class="value">{item[1]}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    st.subheader("Popular learning paths")
    feature_cols = st.columns(3)
    feature_data = [
        ("Python Mastery", "Build logic, coding fluency, and problem-solving confidence.", "Python"),
        ("DSA Excellence", "Practice arrays, trees, graphs, and interview-style problem solving.", "DSA"),
        ("Career Prep", "Prepare for company rounds, internships, and technical interviews.", "Career"),
    ]
    for idx, (title, desc, tag) in enumerate(feature_data):
        with feature_cols[idx]:
            st.markdown(
                f"""
                <div class="feature-card">
                    <div class="tag">{tag}</div>
                    <h4>{title}</h4>
                    <p>{desc}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_courses() -> None:
    st.header("Courses")
    st.caption("Engineered for students who want deep understanding, skill growth, and strong placement readiness.")
    cols = st.columns(3)
    for idx, course in enumerate(COURSE_CATALOG):
        with cols[idx % 3]:
            st.markdown(
                f"""
                <div class="course-card">
                    <div class="meta">{course['level']} · {course['duration']}</div>
                    <h4>{course['title']}</h4>
                    <p>{course['description']}</p>
                    <div style="margin-top: 0.7rem; display:flex; flex-wrap:wrap; gap:0.4rem;">
                        {''.join(f'<span class="nav-chip" style="margin:0;">{tag}</span>' for tag in course['tags'])}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_roadmaps() -> None:
    st.header("Roadmaps")
    st.caption("Smart learning paths designed for academic growth, coding confidence, and career milestones.")
    cols = st.columns(3)
    for idx, roadmap in enumerate(ROADMAPS):
        with cols[idx]:
            st.markdown(
                f"""
                <div class="roadmap-card">
                    <div class="meta" style="margin-bottom:0.6rem;">{roadmap['timeline']}</div>
                    <h4>{roadmap['title']}</h4>
                    <ul>
                        {''.join(f'<li>{item}</li>' for item in roadmap['outcomes'])}
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_ai_tutor() -> None:
    model = configure_model()
    st.header("AI Tutor")
    st.caption("Ask about concepts, projects, coding practice, interviews, and study strategy.")

    if model is None:
        st.info("Demo AI mode is active. The assistant is running locally so the app is fully usable even before you add an API key.")

    col_voice, col_clear = st.columns([4, 1])
    with col_voice:
        voice_result = voice_input_component()
    with col_clear:
        if st.button("Clear history"):
            st.session_state.chat_history = []
            clear_local_chat_messages()
            st.rerun()

    if isinstance(voice_result, str) and voice_result.strip():
        captured = voice_result.strip()
        if captured != st.session_state.get("last_voice_capture"):
            st.session_state.last_voice_capture = captured
            process_chat_prompt(captured, st.selectbox("Subject", ["Python", "Java", "DSA", "DBMS", "OS", "Web Development"], key="tutor_subject"), "Intermediate", "College", model)
            st.rerun()

    render_chat_history()

    prompt = st.chat_input("Ask EduGenie about coding, DSA, Java, Python, systems, or study strategy...")
    if prompt:
        process_chat_prompt(prompt, st.session_state.get("tutor_subject", "Python"), "Intermediate", "College", model)
        st.rerun()


def render_quiz_tab() -> None:
    model = configure_model()
    st.header("Quiz Center")
    if model is None:
        st.info("Quiz demo mode is active so you can test the platform right away.")

    subject = st.selectbox("Subject", ["Python", "Java", "DSA", "DBMS", "OS", "Computer Networks"], key="quiz_subject")
    topic = st.text_input("Topic", value=st.session_state.last_topic, key="quiz_topic")
    level = st.selectbox("Difficulty", ["Beginner", "Intermediate", "Advanced"], key="quiz_level")

    col_gen, col_reset = st.columns([2, 1])
    with col_gen:
        if st.button("Generate quiz"):
            generated = generate_demo_quiz(subject, topic, level) if model is None else generate_quiz(subject, topic, level, model)
            st.session_state.quiz_questions = generated
            st.session_state.quiz_index = 0
            st.session_state.quiz_score = 0
            st.success("Quiz generated successfully.")
    with col_reset:
        if st.button("Reset quiz"):
            st.session_state.quiz_questions = []
            st.session_state.quiz_index = 0
            st.session_state.quiz_score = 0

    render_quiz()


def main() -> None:
    init_session_state()

    nav_tabs = ["Home", "Courses", "AI Tutor", "Quiz", "Roadmaps"]
    active_tab = st.radio(
        "",
        nav_tabs,
        index=nav_tabs.index(st.session_state.active_tab) if st.session_state.active_tab in nav_tabs else 0,
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state.active_tab = active_tab

    if active_tab == "Home":
        render_home()
    elif active_tab == "Courses":
        render_courses()
    elif active_tab == "AI Tutor":
        render_ai_tutor()
    elif active_tab == "Quiz":
        render_quiz_tab()
    else:
        render_roadmaps()


if __name__ == "__main__":
    main()

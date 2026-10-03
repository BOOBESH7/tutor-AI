import logging
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from explanation_module import explain_topic
from auth_service import FirebaseAuthUnavailable, verify_firebase_id_token
from database import (
    get_chat_history,
    initialize_database,
    migrate_legacy_chat_history_file,
    save_chat_history,
)
from gemini_service import GeminiServiceError
from learning_path import recommend_learning_path
from qna import answer_question
from quiz_module import generate_quiz
from summary_module import summarize_text

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    migrate_legacy_chat_history_file(BASE_DIR / "chat_history.json")
    yield


app = FastAPI(title="EduGenie AI Tutor", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

COURSE_CATALOG = [
    {
        "title": "Python for Engineering",
        "level": "Beginner to Advanced",
        "duration": "6 weeks",
        "description": "Master Python fundamentals, automation, OOP, and coding logic for engineering tasks.",
        "tags": ["Python", "Automation", "OOP"],
    },
    {
        "title": "Data Structures & Algorithms",
        "level": "Intermediate",
        "duration": "8 weeks",
        "description": "Learn arrays, trees, graphs, recursion, and interview-focused problem-solving patterns.",
        "tags": ["DSA", "Problem solving", "Interview"],
    },
    {
        "title": "Java & Core Concepts",
        "level": "Intermediate",
        "duration": "7 weeks",
        "description": "Learn Java classes, inheritance, collections, and backend fundamentals used in modern systems.",
        "tags": ["Java", "OOP", "Backend"],
    },
    {
        "title": "DBMS & SQL",
        "level": "Intermediate",
        "duration": "5 weeks",
        "description": "Understand SQL, database modeling, normalization, transactions, and schema design.",
        "tags": ["DBMS", "SQL", "Data"],
    },
    {
        "title": "Operating Systems",
        "level": "Advanced",
        "duration": "4 weeks",
        "description": "Explore scheduling, memory, process management, and system resource allocation.",
        "tags": ["OS", "Systems", "Architecture"],
    },
    {
        "title": "Computer Networks",
        "level": "Intermediate",
        "duration": "4 weeks",
        "description": "Study TCP/IP, routing, protocols, and the core communication fundamentals of distributed systems.",
        "tags": ["Networking", "Protocols", "Security"],
    },
    {
        "title": "Generative AI Fundamentals",
        "level": "Beginner to Intermediate",
        "duration": "4 weeks",
        "description": "Learn prompt engineering, model reasoning, and real-world applications of Generative AI in education and software.",
        "tags": ["AI", "Gemini", "Prompting"],
    },
    {
        "title": "Cloud Computing Basics",
        "level": "Beginner",
        "duration": "3 weeks",
        "description": "Understand cloud deployment, architecture, security, and how AI services work in production environments.",
        "tags": ["Cloud", "Deployment", "Architecture"],
    },
]

ROADMAPS = [
    {
        "title": "Full-Stack Developer Roadmap",
        "timeline": "12 weeks",
        "outcomes": ["Frontend basics", "Python/Flask", "Database design", "Deployment"],
    },
    {
        "title": "DSA Mastery Path",
        "timeline": "10 weeks",
        "outcomes": ["Arrays", "Linked lists", "Trees", "Graphs", "Interview drills"],
    },
    {
        "title": "AI & Cloud Learning Track",
        "timeline": "8 weeks",
        "outcomes": ["Generative AI", "Prompt design", "Cloud basics", "Real world projects"],
    },
    {
        "title": "Placement Preparation Roadmap",
        "timeline": "6 weeks",
        "outcomes": ["Core CS revision", "Mock tests", "Resume projects", "Interview practice"],
    },
]

LEARNING_PATHS = [
    {
        "title": "Python + DSA Path",
        "focus": "Logic, problem solving, interview practice",
        "timeline": "8 weeks",
        "steps": ["Python basics", "Functions and data structures", "Lists, stacks, queues", "Trees and graphs", "Interview drills"],
    },
    {
        "title": "Java + OOP Path",
        "focus": "Object-oriented programming and backend thinking",
        "timeline": "7 weeks",
        "steps": ["Java syntax", "Classes and inheritance", "Collections", "Exception handling", "Mini projects"],
    },
    {
        "title": "AI + Cloud Path",
        "focus": "Generative AI and deployment",
        "timeline": "6 weeks",
        "steps": ["Prompt design", "Gemini usage", "API integration", "Cloud basics", "Deploy a project"],
    },
]

FEATURE_ITEMS = [
    {"title": "AI Q&A Tutor", "description": "Get clear answers to engineering concepts, coding questions, and course topics in simple language."},
    {"title": "Quiz Generator", "description": "Create topic-based MCQs for practice and self-check your understanding after each study session."},
    {"title": "Summary Assistant", "description": "Turn long notes, chapters, and study material into short and readable summaries for faster revision."},
    {"title": "Learning Roadmaps", "description": "Follow structured learning paths designed for placement preparation, coding growth, and skill mastery."},
]


def fallback_answer(question: str, subject: str, level: str, reason: Any) -> str:
    """Offline reply so the chat box always responds, even when AI is unavailable."""
    return (
        "**Local reply** (the AI service is not reachable right now)\n\n"
        f"I received your question: **{question}**\n\n"
        f"- Subject: {subject}\n"
        f"- Level: {level}\n\n"
        "**How to move forward:**\n\n"
        "1. Split the question into the smallest part you are unsure about.\n"
        "2. Write a tiny example and run it, or dry-run the steps on paper.\n"
        "3. Read the exact error message and note the line it points to.\n\n"
        f"_AI skipped because: {reason}_"
    )


class ChatRequest(BaseModel):
    question: str | None = Field(default=None, max_length=10000)
    message: str | None = Field(default=None, max_length=10000)
    subject: str = "Python"
    level: str = "Intermediate"
    age_group: str = "College"


class ExplainRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=5000)


class QuizRequest(BaseModel):
    text: str | None = Field(default=None, max_length=30000)
    subject: str = "General"
    topic: str | None = Field(default=None, max_length=5000)
    level: str = "Intermediate"


class SummaryRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000)


class LearningPlanRequest(BaseModel):
    topic: str | None = Field(default=None, max_length=5000)
    subject: str = "Python"
    goal: str = "Placement preparation"
    level: str = "Intermediate"


auth_scheme = HTTPBearer(auto_error=False)


def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(auth_scheme)) -> Dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Sign in with your verified email to use EduGenie.")
    try:
        return verify_firebase_id_token(credentials.credentials)
    except FirebaseAuthUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        status_code = 403 if str(exc).startswith("Please verify") else 401
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


def optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(auth_scheme),
) -> Dict[str, Any] | None:
    if credentials is None:
        return None
    return require_user(credentials)


def run_ai(operation):
    try:
        return operation()
    except GeminiServiceError as exc:
        status_code = 503 if "not configured" in str(exc).lower() else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except (ValueError, TypeError):
        logger.warning("Gemini returned content that did not match the requested format.", exc_info=True)
        raise HTTPException(status_code=502, detail="The AI response was not in the expected format. Please try again.")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="home.html", context={})


@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request):
    return templates.TemplateResponse(request=request, name="home.html", context={})


@app.get("/courses", response_class=HTMLResponse)
def courses_page(request: Request):
    return templates.TemplateResponse(request=request, name="courses.html", context={})


@app.get("/ai-tutor", response_class=HTMLResponse)
def ai_tutor_page(request: Request):
    return templates.TemplateResponse(request=request, name="ai_tutor.html", context={})


@app.get("/quiz", response_class=HTMLResponse)
def quiz_page(request: Request):
    return templates.TemplateResponse(request=request, name="quiz.html", context={})


@app.get("/roadmaps", response_class=HTMLResponse)
def roadmaps_page(request: Request):
    return templates.TemplateResponse(request=request, name="roadmaps.html", context={})


@app.get("/features", response_class=HTMLResponse)
def features_page(request: Request):
    return templates.TemplateResponse(request=request, name="features.html", context={})


@app.get("/summarizer", response_class=HTMLResponse)
def summarizer_page(request: Request):
    return templates.TemplateResponse(request=request, name="summarizer.html", context={})


@app.get("/learning-paths", response_class=HTMLResponse)
def learning_paths_page(request: Request):
    return templates.TemplateResponse(request=request, name="learning_paths.html", context={})


@app.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    return templates.TemplateResponse(request=request, name="about.html", context={})


@app.get("/contact", response_class=HTMLResponse)
def contact_page(request: Request):
    return templates.TemplateResponse(request=request, name="contact.html", context={})


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "EduGenie AI Tutor",
        "gemini_configured": os.getenv("GEMINI_API_KEY", "").strip() not in ("", "YOUR_GEMINI_API_KEY"),
        "timestamp": datetime.utcnow().isoformat(),
        "database": "sqlite",
    }


@app.get("/api/config")
def public_firebase_config() -> Dict[str, str]:
    project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
    return {
        "apiKey": os.getenv("FIREBASE_API_KEY", "").strip(),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", f"{project_id}.firebaseapp.com" if project_id else "").strip(),
        "projectId": project_id,
        "appId": os.getenv("FIREBASE_APP_ID", "").strip(),
    }


@app.get("/api/history")
def get_history(user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    try:
        return {"history": get_chat_history(str(user["uid"]))}
    except Exception as exc:
        logger.warning("Could not load EduGenie chat history from the local database.", exc_info=True)
        raise HTTPException(status_code=503, detail="Chat history is temporarily unavailable.") from exc


@app.get("/api/courses")
def get_courses() -> Dict[str, Any]:
    return {"courses": COURSE_CATALOG}


@app.get("/api/roadmaps")
def get_roadmaps() -> Dict[str, Any]:
    return {"roadmaps": ROADMAPS}


@app.get("/api/learning-paths")
def get_learning_paths() -> Dict[str, Any]:
    return {"paths": LEARNING_PATHS}


@app.get("/api/features")
def get_features() -> Dict[str, Any]:
    return {"features": FEATURE_ITEMS}


@app.post("/qa")
@app.post("/api/chat")
def chat(req: ChatRequest, user: Dict[str, Any] | None = Depends(optional_user)) -> Dict[str, Any]:
    question = (req.question or req.message or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Enter a question first.")
    try:
        answer = run_ai(lambda: answer_question(question, req.subject, req.level, req.age_group))
    except HTTPException as exc:
        logger.warning("Gemini was unavailable for /qa; using the offline fallback reply.", exc_info=True)
        answer = fallback_answer(question, req.subject, req.level, exc.detail)
    history_saved = (
        save_chat_history(user_id=str(user["uid"]), question=question, answer=answer, feature="qa")
        if user
        else False
    )
    return {
        "success": True,
        "answer": answer,
        "message": answer,
        "subject": req.subject,
        "level": req.level,
        "history_saved": history_saved,
        "history_warning": (
            None
            if history_saved or user is None
            else "Your answer is ready, but chat history could not be saved right now."
        ),
    }


@app.post("/explain")
def explain(req: ExplainRequest, _: Dict[str, Any] | None = Depends(optional_user)) -> Dict[str, Any]:
    return {"success": True, "explanation": run_ai(lambda: explain_topic(req.topic.strip()))}


@app.post("/quiz")
@app.post("/api/quiz")
def quiz(req: QuizRequest, _: Dict[str, Any] | None = Depends(optional_user)) -> Dict[str, Any]:
    source = (req.text or req.topic or "").strip()
    if not source:
        raise HTTPException(status_code=400, detail="Enter a topic or passage for the quiz.")
    questions = run_ai(lambda: generate_quiz(source, req.subject, req.level))
    return {"success": True, "questions": questions, "subject": req.subject, "topic": req.topic or source, "level": req.level}


@app.post("/summarize")
@app.post("/api/summarize")
def summarize(req: SummaryRequest, _: Dict[str, Any] | None = Depends(optional_user)) -> Dict[str, Any]:
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Paste some text to summarize.")
    return {"success": True, "summary": run_ai(lambda: summarize_text(req.text.strip()))}


@app.post("/learn/recommendations")
@app.post("/api/learning-plan")
def learning_plan(req: LearningPlanRequest, _: Dict[str, Any] | None = Depends(optional_user)) -> Dict[str, Any]:
    topic = (req.topic or req.subject).strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Enter a learning topic.")
    plan = run_ai(lambda: recommend_learning_path(topic, req.goal, req.level))
    return {
        "success": True,
        "learning_path": plan,
        "plan": json.dumps(plan, indent=2),
        "topic": topic,
        "goal": req.goal,
        "level": req.level,
    }


@app.get("/api/demo")
def demo() -> Dict[str, Any]:
    return {
        "message": "Configure GEMINI_API_KEY and Firebase Authentication to use all features.",
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)

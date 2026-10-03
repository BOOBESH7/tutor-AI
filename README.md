# EduGenie: Gemini-Powered Learning Assistant

EduGenie is a student learning assistant built with FastAPI, HTML, CSS, and JavaScript. Students can ask questions, get explanations, generate quizzes, summarize notes, and create learning paths. It uses SQLite on your computer for chat history and Firebase Authentication for Google or email sign-in.

## Features

- Gemini-powered Q&A, explanations, quizzes, summaries, and learning recommendations
- Readable formatted AI answers with clear headings, lists, and code examples across features
- Guest access to every learning tool; optional Google/email sign-in to save private chat history
- Interactive quizzes with answer feedback
- Private per-account chat history stored in a local SQLite database
- AI-generated, personalized roadmaps for learner-entered topics and goals
- Responsive course and roadmap pages
- FastAPI validation and OpenAPI docs at `/docs`

## Technology

- Python 3.10 or later, FastAPI, Uvicorn, and Jinja2
- SQLite (built into Python) for local chat history
- Gemini API for AI responses
- Firebase Authentication for Google and email sign-in

## Project layout

```text
.
├── main.py
├── auth_service.py
├── database.py
├── gemini_service.py
├── qna.py
├── explanation_module.py
├── quiz_module.py
├── summary_module.py
├── learning_path.py
├── requirements.txt
├── .env.example
├── .gitignore
├── templates/
└── static/
```

## Configuration

1. Copy `.env.example` to `.env`.
2. Set `GEMINI_API_KEY` to your Gemini API key. AI features use this key; Google Cloud and Vertex AI credentials are not used.
3. Set the Firebase web app values: `FIREBASE_PROJECT_ID`, `FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN`, and `FIREBASE_APP_ID`.
4. Enable Google in Firebase Authentication > Sign-in method. Use `http://localhost:8000` locally; if you browse to `127.0.0.1`, add `127.0.0.1` under Authentication > Settings > Authorized domains. Add the exact Vercel hostname for production (for example, `tutor-ai-eight-liard.vercel.app`) in the same settings. Project-owner permission may be required. The app uses a popup on desktop and automatically uses redirect sign-in on mobile or if the browser blocks the popup.

The SQLite database is created automatically at `data/edugenie.sqlite3` when the app starts locally. On Vercel it defaults to the writable temporary directory because the deployed project files are read-only; that temporary database is not durable and chat history may be lost between function instances or deployments. Existing Streamlit chat messages in `chat_history.json` are imported into SQLite once; the JSON file is left in place as a backup. The database does not require Firestore, a service-account file, or Google Cloud database setup. You can change its location with `DATABASE_PATH`. The `.db` and `.sqlite3` files are excluded from Git.

The learning tools are available without signing in. Guest chats are not saved; signing in is optional and enables per-account chat history. Firebase sign-in and Gemini answers require an internet connection. Firebase is used only for authentication; chat history stays in the local SQLite database.

## Environment variables

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-3.1-flash-lite
DATABASE_PATH=data/edugenie.sqlite3
FIREBASE_PROJECT_ID=YOUR_FIREBASE_PROJECT_ID
FIREBASE_API_KEY=YOUR_FIREBASE_WEB_API_KEY
FIREBASE_AUTH_DOMAIN=YOUR_FIREBASE_PROJECT_ID.firebaseapp.com
FIREBASE_APP_ID=YOUR_FIREBASE_WEB_APP_ID
PORT=8000
```

Keep `.env` private. Never commit API keys or service-account credentials.

## Install and run on Windows

In PowerShell, from the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
if (!(Test-Path .env)) { Copy-Item .env.example .env }
python -m pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000). Use the learning tools immediately without an account; sign in only if you want to save chat history. If the local site does not open, confirm the server command is still running in the terminal.

## API endpoints

Learning endpoints require a Firebase ID token; the browser adds this after sign-in.

| Method | Path | Request body |
|---|---|---|
| POST | `/qa` | `{"question":"What is photosynthesis?"}` |
| POST | `/explain` | `{"topic":"Quantum Computing"}` |
| POST | `/quiz` | `{"text":"Photosynthesis is the process..."}` |
| POST | `/summarize` | `{"text":"Educational passage..."}` |
| POST | `/learn/recommendations` | `{"topic":"Python Programming"}` |

`/api/history` returns the signed-in user's latest 50 Q&A records from SQLite. `/docs` provides the OpenAPI interface.

## Testing

Run the local unit tests with:

```powershell
python -m unittest discover -s tests -v
```

For a manual check, open `/`, `/docs`, and `/api/health`, sign in, ask a question, and confirm that a local `data/edugenie.sqlite3` file is created.

"""Vercel serverless entrypoint for the EduGenie FastAPI application."""
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from main import app
except Exception:
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse

    _STARTUP_TRACEBACK = traceback.format_exc()
    app = FastAPI(title="EduGenie startup error")

    @app.get("/{path:path}")
    def _startup_error(path: str) -> PlainTextResponse:
        return PlainTextResponse("EduGenie could not start.\n\n" + _STARTUP_TRACEBACK, status_code=500)

"""Root entry point so 'uvicorn main:app' works (e.g. Railway/Render default)."""
from app.main import app

__all__ = ["app"]

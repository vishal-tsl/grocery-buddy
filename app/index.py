"""
Vercel serverless entry point. Exposes the FastAPI app at a standard path
so Vercel can run it (app/index.py, app/server.py, or app/app.py).
"""
from app.main import app

__all__ = ["app"]

# Ensure project root is on path when Vercel runs from api/
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from app.main import app

__all__ = ["app"]

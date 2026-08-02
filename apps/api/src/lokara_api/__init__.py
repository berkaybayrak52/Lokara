"""Lokara FastAPI backend — one HTTP/JSON API for web + mobile (docs/01)."""

from .main import app, create_app

__version__ = "0.1.0"

__all__ = ["app", "create_app"]

"""Gunicorn config — binds to Render's PORT (set automatically on deploy)."""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
workers = 1

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

# MyMemory (Google Translate backend, free tier)
MYMEMORY_URL = os.environ.get(
    "MYMEMORY_URL", "https://api.mymemory.translated.net/get"
).rstrip("/")
MYMEMORY_EMAIL = os.environ.get("MYMEMORY_EMAIL", "")

# Glosbe bilingual examples
GLOSBE_URL = os.environ.get(
    "GLOSBE_URL", "https://glosbe.com/gapi/v0.1/translate"
).rstrip("/")
GLOSBE_USER_AGENT = os.environ.get(
    "GLOSBE_USER_AGENT", "EstudioPersonal/1.0 (student project)"
)

# DictionaryAPI.dev (no key)
DICTIONARY_API_BASE = os.environ.get(
    "DICTIONARY_API_BASE", "https://api.dictionaryapi.dev/api/v2/entries/en"
).rstrip("/")

# Lingua Robot — optional grammar / conjugation
LINGUA_ROBOT_ENABLED = os.environ.get("LINGUA_ROBOT_ENABLED", "true").lower() == "true"
LINGUA_ROBOT_BASE = os.environ.get(
    "LINGUA_ROBOT_BASE", "https://www.lingua-robot.com/api/v1"
).rstrip("/")

SCHEDULER_ENABLED = os.environ.get("SCHEDULER_ENABLED", "true").lower() == "true"

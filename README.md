# Estudio Abroad

Estudio Abroad is a Spanish-first study app built for students preparing for a term in Barcelona. It teaches practical, everyday language — transit phrases, market vocabulary, travel tips — through reading in context rather than textbook drills. English stays hidden until you hover or click to reveal it, so you practice inferring meaning before checking the translation. Register with your email to save a personal phrasebook, track XP and weak words, and upload a profile photo — all stored in per-user JSON files alongside a shared API cache.

## Demo

https://cursor-spanishstudy-xander.onrender.com

## Features

- **Inicio** — Daily Spanish word and sentence, weak-words ranking from flashcards, XP/streak stats
- **Cuenta** — Register/login with email and password; upload a profile picture; per-user progress and phrasebook
- **Lector** — Fog-reveal reader: a cursor lens uncovers English under Spanish passages; includes daily rotating Spain-related Wikipedia articles
- **Tarjetas** — Flashcard deck; mark misses to build your weak-words list
- **Libro de frases** — Type English → cached Spanish translation; add, edit, delete; export CSV
- **Voz** — Speak English or Spanish; real-time translation via MyMemory (browser speech recognition)
- **Viajes** — Filter Barcelona recommendations by time, location, distance, and mood; Leaflet map
- **Noticias** — Spanish headlines about Spain (NewsAPI, cached 60 minutes)
- **Historia** — Four Spain/Catalonia topics with click-to-reveal English summaries
- **Recursos** — Curated Spanish study links

## Tech Stack

- Python 3 / Flask
- Bootstrap 5 (Bootstrap-style components via custom CSS)
- NewsAPI (headlines); MyMemory (translations); DictionaryAPI.dev (definitions)
- APScheduler
- Deployed on Render

## Setup

### Prerequisites

- Python 3.11+
- A NewsAPI key (get one at [newsapi.org/register](https://newsapi.org/register))

### Installation

```bash
git clone https://github.com/xandermckie/studyspanish
cd studyspanish
python -m venv .venv
pip install -r requirements.txt
```

Activate the virtual environment before running the app:

- **Windows (PowerShell):** `.\.venv\Scripts\Activate.ps1`
- **macOS / Linux:** `source .venv/bin/activate`

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```
FLASK_DEBUG=1
SECRET_KEY=change-me
NEWS_API_KEY=your_key_here
SCHEDULER_ENABLED=true
REFRESH_INTERVAL_MINUTES=15
```

Optional variables (defaults shown in `.env.example`):

| Variable | Purpose |
|----------|---------|
| `MYMEMORY_EMAIL` | Optional email for higher MyMemory rate limits |
| `MYMEMORY_URL` | MyMemory API endpoint (default provided) |
| `DICTIONARY_API_BASE` | DictionaryAPI.dev endpoint (no key required) |
| `NEWS_API_URL` | NewsAPI endpoint (default provided) |

The news section requires `NEWS_API_KEY`; the rest of the app works without it.

### Run Locally

```bash
export FLASK_APP=app   # macOS/Linux
flask run
```

On Windows PowerShell:

```powershell
$env:FLASK_APP = "app"
flask run
```

Alternatively: `flask --app app run` (no env var needed).

Open http://localhost:5000

On first run, the app creates `data/cache.json` automatically.

### Account

1. Open http://localhost:5000/register and create an account with your email and password (minimum 8 characters).
2. Sign in at `/login`. Your phrasebook, flashcard progress, weak words, and XP are saved under `data/users/{user_id}.json`.
3. Upload a profile photo at `/profile` (JPG, PNG, or WebP, max 2 MB).

You can browse the reader, news, and travel pages without signing in. Phrasebook saves and flashcard scoring require an account.

**Note:** On Render's free tier, disk storage is ephemeral — user files may not survive redeploys. Use local development for persistent testing.

### Development

Install dev dependencies and run the test suite:

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Tests use a temporary `data/` directory (via `pytest.ini` + fixtures in `tests/conftest.py`) so your local cache and user files are not modified.

## How It Works

Estudio Abroad is a Flask app with no database. Shared content (daily word, translations, news, reader passages) lives in `data/cache.json`. Each registered user gets their own JSON file at `data/users/{user_id}.json` for phrasebook entries, weak words, vocab session progress, and XP stats. Profile photos are stored under `data/uploads/{user_id}/`.

When you load the homepage or flip a flashcard while signed in, Flask reads your user file through `user_store.py` and `fetcher.py`, then renders Jinja2 templates. Anonymous visitors see shared content only; progress and phrases require login.

On startup, `scheduler.py` registers an APScheduler background job that runs every 15 minutes (configurable via `REFRESH_INTERVAL_MINUTES`). Each run calls `fetcher.run_refresh()`, which refreshes the daily word and sentence, reader passages, flashcard deck, Wikipedia articles for the reader, and (when `NEWS_API_KEY` is set) Spanish news headlines. Wikipedia articles about Spain (history, culture, cuisine, landmarks) are fetched from the Spanish Wikipedia API, cached for 24 hours, and rotated daily in the reader. Translation requests go through the MyMemory API, but every lookup is keyed by a SHA hash and stored under `cache["translations"]` so repeat phrases never hit the network. DictionaryAPI.dev enriches the daily word with phonetics and an English definition. News articles are filtered for Spain-related keywords and cached for an hour.

The UI is Spanish-first: English appears only on hover (site-wide click-to-reveal) or through the reader's fog lens, which follows your cursor over a passage. Signed-in users track flashcard misses in their personal `weak_words` map, surfaced on the homepage. Phrasebook entries are translated once via MyMemory and cached per user.

## What I'd Build Next

- **Rebuild the quiz page** — A prior quiz route was removed; a new version would mix Open Trivia DB questions with personal vocab and score by category
- **Spaced repetition** — Resurface weak flashcard words more often instead of cycling the deck in flat order
- **Persistent storage on Render** — Free-tier disk is ephemeral; move cache and phrasebook data to Postgres or S3 so user progress survives redeploys
- **Audio pronunciation** — Integrate something like the Forvo API for native Catalan and Spanish listening practice
- **Offline / PWA mode** — Service worker over cached JSON so the app works without a network connection

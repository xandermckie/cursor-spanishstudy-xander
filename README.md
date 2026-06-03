# Estudio Abroad

Estudio Abroad is a Spanish-first study app built for students preparing for a term in Barcelona. It teaches practical, everyday language — transit phrases, market vocabulary, travel tips — through reading in context rather than textbook drills. English stays hidden until you hover or click to reveal it, so you practice inferring meaning before checking the translation. The fog-reveal reader, flashcards, personal phrasebook, and Barcelona travel guide are all backed by a single JSON cache with background API refresh.

## Demo

https://cursor-spanishstudy-xander.onrender.com

## Features

- **Inicio** — Daily Spanish word and sentence, weak-words ranking from flashcards, XP/streak stats
- **Lector** — Fog-reveal reader: a cursor lens uncovers English under Spanish/Catalan passages
- **Tarjetas** — Flashcard deck; mark misses to build your weak-words list
- **Libro de frases** — Type English → cached Spanish translation; add, edit, delete; export CSV
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

## How It Works

Estudio Abroad is a Flask app with no database. Every route in `app.py` calls functions in `fetcher.py`, which read and write a single JSON file at `data/cache.json`. When you load the homepage, open the reader, or flip a flashcard, Flask pulls pre-built data from that cache and renders it through Jinja2 templates. User actions — marking a flashcard miss, adding a phrase, earning XP — write back to the same file.

On startup, `scheduler.py` registers an APScheduler background job that runs every 15 minutes (configurable via `REFRESH_INTERVAL_MINUTES`). Each run calls `fetcher.run_refresh()`, which refreshes the daily word and sentence, reader passages, flashcard deck, and (when `NEWS_API_KEY` is set) Spanish news headlines. Translation requests go through the MyMemory API, but every lookup is keyed by a SHA hash and stored under `cache["translations"]` so repeat phrases never hit the network. DictionaryAPI.dev enriches the daily word with phonetics and an English definition. News articles are filtered for Spain-related keywords and cached for an hour.

The UI is Spanish-first: English appears only on hover (site-wide click-to-reveal) or through the reader's fog lens, which follows your cursor over a passage. Flashcard sessions track misses in `cache["weak_words"]`, and those counts surface on the homepage so you know what to drill next. Phrasebook entries are translated once via MyMemory, cached, and persist across sessions in the same JSON file.

## What I'd Build Next

- **Rebuild the quiz page** — A prior quiz route was removed; a new version would mix Open Trivia DB questions with personal vocab and score by category
- **Spaced repetition** — Resurface weak flashcard words more often instead of cycling the deck in flat order
- **Persistent storage on Render** — Free-tier disk is ephemeral; move cache and phrasebook data to Postgres or S3 so user progress survives redeploys
- **Audio pronunciation** — Integrate something like the Forvo API for native Catalan and Spanish listening practice
- **Offline / PWA mode** — Service worker over cached JSON so the app works without a network connection

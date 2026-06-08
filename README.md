# Estudio Abroad

Estudio Abroad is a Spanish-first study app built for students preparing for a term in Barcelona. It teaches practical, everyday language — transit phrases, market vocabulary, travel tips — through reading in context rather than textbook drills. English stays hidden until you hover or click to reveal it, so you practice inferring meaning before checking the translation. Register with your email to save a personal phrasebook, track XP and weak words, and upload a profile photo — all stored in encrypted per-user JSON files alongside a shared API cache.

## Demo

https://cursor-spanishstudy-xander.onrender.com

## Features

- **Inicio** — Daily Spanish word and sentence, weak-words ranking from flashcards, XP/streak stats
- **Cuenta** — Register/login with email and password; upload a profile picture; per-user progress and phrasebook
- **Lector** — Fog-reveal reader: a cursor lens uncovers English under Spanish passages; includes daily rotating Spain-related Wikipedia articles
- **Tarjetas** — Flashcard deck; mark misses to build your weak-words list (sequential sessions, server-validated)
- **Libro de frases** — Personal phrase list with click-to-reveal English; add, edit, delete; export CSV
- **Traductor** — Translate between English, Spanish, and Catalan; save EN/ES pairs to your phrasebook when signed in
- **Voz** — Voice translation (English ↔ Spanish): keyboard dictation on mobile, Whisper on desktop; save to phrasebook when signed in
- **Viajes** — Filter Barcelona recommendations by time, location, distance, and mood; Google Maps with walking routes
- **Noticias** — Spanish headlines about Spain (NewsAPI, cached 60 minutes)
- **Historia** — Four Spain/Catalonia topics with click-to-reveal English summaries
- **Recursos** — Curated Spanish study links

## Tech Stack

- Python 3 / Flask
- Bootstrap-style UI via custom CSS (`static/css/estudio.css`)
- Translation: Lingva, MyMemory, and optional LibreTranslate (parallel race; results cached in JSON)
- DictionaryAPI.dev (definitions); Spanish Wikipedia API (reader articles)
- NewsAPI (headlines); Google Maps / Places (travel)
- Fernet encryption for user data at rest (`cryptography`)
- APScheduler (background cache refresh)
- Deployed on Render via Gunicorn

## Deploy on Render

Repo: [`xandermckie/cursor-spanishstudy-xander`](https://github.com/xandermckie/cursor-spanishstudy-xander), branch `main`.

| Setting | Value |
|---------|--------|
| **Root Directory** | *(leave blank)* |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | *(leave blank — uses `Procfile`)* **or** `gunicorn -c gunicorn.conf.py app:app` |

Do **not** use `gunicorn app:app` alone — it ignores Render’s `PORT`. The repo’s [`Procfile`](Procfile) and [`gunicorn.conf.py`](gunicorn.conf.py) bind to `0.0.0.0:$PORT` for you.

**Environment (recommended on Render):**

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Session signing and encryption key derivation |
| `MYMEMORY_EMAIL` | Raises shared-server MyMemory quota (5k → 50k chars/day) |
| `LINGVA_URLS` | Comma-separated Lingva instances (default: `https://lingva.ml/api/v1`) |
| `NEWS_API_KEY` | Live Spanish news headlines |
| `GOOGLE_MAPS_API_KEY` | Travel map (Maps JavaScript API + Directions API) |
| `GOOGLE_PLACES_API_KEY` | Optional server-side place recommendations on `/travel` |

Optional: `LIBRETRANSLATE_URL` for an extra translation fallback; `ENCRYPTION_KEY` for a dedicated Fernet key (otherwise derived from `SECRET_KEY`).

**Remove** any dashboard `ENCRYPTION_KEY` that Render auto-generated; it is not a valid Fernet key.

On first boot the app **seeds the homepage from built-in data** (no API wait) and runs a **full cache refresh immediately** when the scheduler starts, so Inicio is not empty on a cold Render deploy.

[`render.yaml`](render.yaml) is an optional Blueprint with the same defaults.

## Setup

### Prerequisites

- Python 3.11+
- A NewsAPI key for live headlines ([newsapi.org/register](https://newsapi.org/register)) — optional for local dev

### Installation

```bash
git clone https://github.com/xandermckie/cursor-spanishstudy-xander.git
cd cursor-spanishstudy-xander
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
| `ENCRYPTION_KEY` | Fernet key for user data at rest; generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. If unset, derived from `SECRET_KEY`. |
| `MYMEMORY_EMAIL` | Optional email for higher MyMemory rate limits |
| `MYMEMORY_URL` | MyMemory API endpoint (default provided) |
| `LINGVA_URLS` | Comma-separated Lingva instances tried in parallel (default: `https://lingva.ml/api/v1`) |
| `LIBRETRANSLATE_URL` | Optional LibreTranslate endpoint for an extra fallback |
| `DICTIONARY_API_BASE` | DictionaryAPI.dev endpoint (no key required) |
| `NEWS_API_URL` | NewsAPI endpoint (default provided) |
| `GOOGLE_MAPS_API_KEY` | Embedded travel map and walking routes — enable **Maps JavaScript API** and **Directions API** in Google Cloud Console |
| `GOOGLE_PLACES_API_KEY` | Optional server-side place recommendations on `/travel` |

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

**VS Code / Cursor:** Use the **Flask: Estudio Abroad (reload)** launch configuration in [`.vscode/launch.json`](.vscode/launch.json) — it loads `.env` and opens the browser automatically.

### Account

1. Open http://localhost:5000/register and create an account with your email and password (minimum 8 characters).
2. Sign in at `/login`. Your phrasebook, flashcard progress, weak words, and XP are saved under `data/users/{user_id}.json` (encrypted).
3. Upload a profile photo at `/profile` (JPG, PNG, or WebP, max 2 MB).

You can browse the reader, news, travel, and translator pages without signing in. Phrasebook saves and flashcard scoring require an account.

**Note:** On Render's free tier, disk storage is ephemeral — user files may not survive redeploys. Use local development for persistent testing.

### Development

Install dev dependencies and run the test suite:

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Tests use a temporary `data/` directory (via `pytest.ini` + fixtures in `tests/conftest.py`) so your local cache and user files are not modified.

## Spain gallery images

Home and several inner pages use photos under `static/img/spain/`. To refresh assets (Wikimedia Commons, 330px thumbs) or regenerate color placeholders when offline:

```bash
python scripts/download_spain_images.py
```

Attribution: images are sourced from Wikimedia Commons when download succeeds; otherwise flat PNG placeholders are generated locally.

## How It Works

Estudio Abroad is a Flask app with no database. Shared content (daily word, translations, news, reader passages) lives in `data/cache.json`. Each registered user gets their own encrypted JSON file at `data/users/{user_id}.json` for phrasebook entries, weak words, vocab session progress, and XP stats. Profile photos are stored under `data/uploads/{user_id}/`.

When you load the homepage or flip a flashcard while signed in, Flask reads your user file through `user_store.py` and `fetcher.py`, then renders Jinja2 templates. Anonymous visitors see shared content only; progress and phrases require login.

On startup, `scheduler.py` registers an APScheduler background job that runs every 15 minutes (configurable via `REFRESH_INTERVAL_MINUTES`). Each run calls `fetcher.run_refresh()`, which refreshes the daily word and sentence, reader passages, flashcard deck, Wikipedia articles for the reader, and (when `NEWS_API_KEY` is set) Spanish news headlines. Wikipedia articles about Spain (history, culture, cuisine, landmarks) are fetched from the Spanish Wikipedia API, cached for 24 hours, and rotated daily in the reader.

**Translation pipeline:** Lookups are keyed by a SHA hash and stored under `cache["translations"]` so repeat phrases never hit the network. On a cache miss, `fetcher.py` races Lingva instances, MyMemory, and (when configured) LibreTranslate in parallel — the first valid result wins. Lingva is tried first because MyMemory’s free quota is per server IP and exhausts quickly on shared Render hosts. The **Traductor** and **Voz** pages share this stack; voice uses shorter per-provider timeouts via `fetch_translation_fast()`.

DictionaryAPI.dev enriches the daily word with phonetics and an English definition. News articles are filtered for Spain-related keywords and cached for an hour.

The UI is Spanish-first: English appears only on hover (site-wide click-to-reveal) or through the reader's fog lens, which follows your cursor over a passage. Signed-in users track flashcard misses in their personal `weak_words` map, surfaced on the homepage. Phrasebook entries store EN/ES pairs; the Traductor page can save bilingual pairs directly, while the phrasebook form still translates English input via the shared cache.

The **Voz** page uses a hybrid speech stack. On phones and tablets, users dictate via the **keyboard's built-in mic** into a textarea (no speech-recognition JavaScript — the page loads a ~4 KB `voice-lite.js` bundle). On desktop it lazy-loads [Transformers.js](https://github.com/huggingface/transformers.js) with the `Xenova/whisper-tiny` model (~40 MB on first recording, then cached in IndexedDB). Transcription never hits the server; only the text translation uses the shared provider race. Microphone access requires HTTPS (provided on Render).

## Production security checklist

Before deploying to Render (or any public host):

1. **`SECRET_KEY`** — Set a strong random value (`python -c "import secrets; print(secrets.token_hex(32))"`). The app refuses to start in production (`FLASK_DEBUG=0`) without it. Never use `change-me` or leave it unset.
2. **`ENCRYPTION_KEY`** — Optional but recommended: a dedicated Fernet key for user data at rest. If omitted, encryption is derived from `SECRET_KEY` (rotating `SECRET_KEY` then requires re-encryption).
3. **`FLASK_DEBUG=0`** — Required on Render. Debug mode disables secure session cookies.
4. **HTTPS** — Render terminates TLS automatically. Session cookies use `Secure` when not in debug mode.
5. **Google Maps / Places keys** — Restrict in [Google Cloud Console](https://console.cloud.google.com/):
   - **Maps JavaScript API key** (`GOOGLE_MAPS_API_KEY`): Application restrictions → HTTP referrers → your Render URL and `localhost` for dev. API restrictions → Maps JavaScript API + Directions API only.
   - **Places API key** (`GOOGLE_PLACES_API_KEY`): IP restrictions (server-side only) or separate key with Places API only.
6. **NewsAPI key** — Server-side only; never expose in templates or client JS.
7. **Rate limiting** — Login, register, and translation endpoints are limited per IP (10/min auth, 30/min translation). Optional `TRANSLATION_REQUIRES_AUTH=1` requires login for translation APIs in production.
8. **CI** — GitHub Actions runs `pip-audit`, `pytest`, and gitleaks on every push/PR (see [`.github/workflows/security.yml`](.github/workflows/security.yml)).

## What I'd Build Next

- **Rebuild the quiz page** — A prior quiz route was removed; a new version would mix Open Trivia DB questions with personal vocab and score by category
- **Spaced repetition** — Resurface weak flashcard words more often instead of cycling the deck in flat order
- **Persistent storage on Render** — Free-tier disk is ephemeral; move cache and phrasebook data to Postgres or S3 so user progress survives redeploys
- **Audio pronunciation** — TTS or Forvo API for native Catalan and Spanish listening practice
- **Offline / PWA mode** — Service worker over cached JSON so the app works without a network connection

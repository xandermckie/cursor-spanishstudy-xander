# Estudio Personal

A personal Spanish and Catalan language study web app built for studying abroad in Barcelona. Flask serves HTML templates with Bootstrap 5; vocabulary and your phrasebook live in JSON files on disk.

## Features

- **Dashboard** — daily sentence, weak-area hint, category shortcuts, word-of-the-day with definition and phonetic
- **Fog-reveal reader** — hover a lens over Spanish/Catalan text to reveal English underneath
- **Vocab browser** — 20 Barcelona-themed entries across five categories, example sentences, optional grammar
- **Quiz** — Open Trivia DB plus vocab multiple-choice
- **Phrasebook** — add and store your own ES / CA / EN phrases
- **Refresh** — warm translation, example, dictionary, and grammar caches
- **Export** — download vocab and phrasebook as CSV

## Requirements

- Python 3.11+
- Internet for API calls (cached data used when APIs are unavailable)

## API services

| Service | Purpose | API key |
|---------|---------|---------|
| [MyMemory](https://mymemory.translated.net/) | Translations (Google Translate backend) | No (optional email for higher limits) |
| [Glosbe](https://glosbe.com/) | Bilingual example sentences (`/gapi/v0.1/translate`) | No |
| [DictionaryAPI.dev](https://dictionaryapi.dev/) | English definitions, phonetics, examples | No |
| [Open Trivia DB](https://opentdb.com/) | Quiz questions | No |
| [Lingua Robot](https://www.lingua-robot.com/api/documentation/) | Spanish/Catalan conjugation (optional) | No |

When Glosbe is unreachable, example sentences fall back to MyMemory translation-memory matches.

## Local setup

```powershell
cd studyspanish
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set `SECRET_KEY`. Optionally set `MYMEMORY_EMAIL` for a higher free-tier character limit.

```powershell
flask --app app run
```

Open [http://127.0.0.1:5000/](http://127.0.0.1:5000/).

Optional: visit [http://127.0.0.1:5000/refresh](http://127.0.0.1:5000/refresh) to warm caches.

## Project layout

```
app.py              Flask app factory and routes
config.py           Environment configuration
helpers/            API wrappers and storage
data/               JSON vocab, passages, phrasebook, caches
templates/          Jinja2 HTML templates
```

Runtime cache files are created on first run and listed in `.gitignore`.

## Deploy on Render

1. Push this repository to GitHub.
2. In [Render](https://render.com), create a **Web Service** and connect the repo.
3. Use **Python 3.11**, build command `pip install -r requirements.txt`, start command `gunicorn app:app --bind 0.0.0.0:$PORT` (or use the included `render.yaml`).
4. Set environment variables from `.env.example`.
5. Deploy.

**Note:** Render’s filesystem is ephemeral. Phrasebook entries and API caches reset on redeploy unless you attach a persistent disk.

## Background refresh

APScheduler runs `run_full_refresh()` every 6 hours when `SCHEDULER_ENABLED=true`. Disable locally with `SCHEDULER_ENABLED=false` in `.env` if you prefer manual refresh only.

## License

Personal study project — use and adapt freely.

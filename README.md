# Estudio Personal

Flask skeleton for a Barcelona Spanish/Catalan study app. Routes and API fetchers are stubbed; business logic comes next.

## Structure

```
app.py          Routes (placeholder responses)
fetcher.py      API call stubs (MyMemory, Glosbe, DictionaryAPI, Open Trivia DB)
scheduler.py    APScheduler — refresh every 15 minutes
templates/      index.html (Bootstrap 5 layout)
data/cache.json Runtime cache (gitignored contents under data/)
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
flask --app app run
```

## Routes

| Method | Path | Status |
|--------|------|--------|
| GET | `/` | Placeholder homepage |
| GET | `/reader` | Placeholder fog reader |
| GET | `/vocab` | Placeholder vocab browser |
| GET | `/quiz` | Placeholder quiz |
| GET/POST | `/phrasebook` | Placeholder phrasebook |
| GET | `/refresh` | Runs `fetcher.run_refresh()` stub |
| GET | `/export` | Placeholder export |

## Deploy on Render

Render needs **gunicorn** (included in `requirements.txt`) and this start command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

The repo includes a `Procfile` and `render.yaml`. If deploy fails with **exit 127**, the start command is missing from the environment — set the Render start command to match the Procfile above, or connect the Blueprint from `render.yaml`.

Set `SECRET_KEY` in the Render dashboard (or use `generateValue` in `render.yaml`).

## APIs (stubs in `fetcher.py`)

1. MyMemory — `fetch_translation()`
2. Glosbe — `fetch_glosbe_examples()`
3. DictionaryAPI.dev — `fetch_definition()`
4. Open Trivia DB — `fetch_trivia_questions()`

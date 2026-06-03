# Estudio Abroad

Flask app for studying Spanish before a study-abroad term in Barcelona. Spanish is shown first; English appears on hover. The fog-reveal reader uses a separate lens interaction.

## Features

- **Inicio** — Palabra del día (Spanish prominent), frase del día, palabras débiles from flashcards
- **Lector** — Fog-reveal passages (Spanish/Catalan with English under cursor lens)
- **Tarjetas** — Flashcards; mark misses to build weak-words list
- **Libro de frases** — English input → cached Spanish translation; add, edit, delete, export CSV
- **Viajes** — Filtered Barcelona recommendations with Leaflet map
- **Noticias** — Spain news in Spanish (NewsAPI, cached 60 min)
- **Historia** — Four Wikipedia topics with click-to-reveal English summaries
- **Recursos** — Curated Spanish study links

## APIs (all translation calls cached in `data/cache.json`)

| Service | Use |
|---------|-----|
| [MyMemory](https://mymemory.translated.net/) | EN ↔ ES translation |
| [DictionaryAPI.dev](https://dictionaryapi.dev/) | English definition / phonetic for word of the day |
| [NewsAPI](https://newsapi.org/) | Spanish news (`NEWS_API_KEY` in `.env`) |
| [Wikipedia REST](https://www.mediawiki.org/wiki/API:REST_API) | History topic summaries |

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
flask --app app run
```

## Deploy on Render

- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app --bind 0.0.0.0:$PORT`
- Set `SECRET_KEY` in environment variables

## Routes

| Method | Path |
|--------|------|
| GET | `/` |
| GET | `/reader` |
| GET | `/vocab` |
| POST | `/vocab/record` |
| GET/POST | `/phrasebook` |
| POST | `/phrasebook/<id>/edit` |
| POST | `/phrasebook/<id>/delete` |
| GET | `/phrasebook/export` |
| GET/POST | `/travel` |
| GET | `/news` |
| GET | `/history` |
| GET | `/resources` |

Background refresh runs every 15 minutes via APScheduler (no manual refresh button).

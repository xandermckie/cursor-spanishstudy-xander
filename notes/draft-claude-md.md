# CLAUDE.md

## Project Overview
This project helps users practice Spanish and Catalan through flashcards, voice translation, written translation, keeping an active phrasebook, reading local news and articles in spanish and translating via a fog reveal cursor, and giving activity suggestions based on the user's goals and time limit in the Barcelona area.

## Architecture
Estudio Abroad is a Flask + Jinja2 app where app.py handles routes and auth, fetcher/ (cache, translation, core) pulls from external APIs and owns shared content, and user_store.py + encryption.py handle per-user encrypted JSON in data/users/. Shared stuff (daily word, translations, news, reader passages) lives in data/cache.json, refreshed on a schedule by scheduler.py — and we also have hardcoded seeds in fetcher_seeds.py and fetcher_travel.py so the site still works when APIs are down. Frontend is mostly templates plus scattered static JS (wheel-nav.js, reveal cards, voice-lite/whisper on desktop).

## Key Decisions
Using JSON instead of SQLite because this started as a personal study app with no database complexity — one shared cache file plus encrypted per-user JSON was enough for a demo on Render, and Postgres/SQLite is explicitly deferred until persistence actually matters.
Flask instead of FastAPI because the app is server-rendered pages (fog-reveal reader, flashcards, phrasebook), not an API-first service — Flask + Jinja2 + session auth was the natural fit from day one.

## Constraints
[Hard rules Claude Code must follow]
- Never commit .env or any file containing API keys
- Error handling must be explicit — no bare except clauses
- Every function must have a docstring
- cache all new translation calls, don't break flashcard/CSRF hardening, run tests with python -m pytest tests/ -q, and don't rip out features (voice lesson) without asking.

## Open Questions
Refactor vs. ship: split the bloated fetcher module and add file locking for JSON read-modify-write races, or leave it until after Barcelona?
Known weak spot: load_user() returning None on decrypt/parse failure can make a logged-in user look anonymous and break phrasebook, XP, streak, and weak words — fix that before calling auth production-ready?
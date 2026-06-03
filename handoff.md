# Estudio Abroad — Cursor Handoff

## Project Overview
Flask web app for senior college students studying abroad in Barcelona.
Spanish-first UX: all text displays in Spanish by default; English revealed on hover (site-wide, except flashcards and quizzes).

**Repo:** https://github.com/xandermckie/cursor-spanishstudy-xander  
**Stack:** Python/Flask + Jinja2 templates, no frontend framework  
**Translation:** MyMemory API (`https://api.mymemory.translated.net/get`)  
**Definitions:** DictionaryAPI.dev  
**Cache:** `data/cache.json` (all translation results cached here to stay under rate limits — do not make uncached API calls)  
**Deploy:** Render (gunicorn)

---

## Current File Structure
```
app.py           — Flask app factory + all routes
fetcher.py       — All API calls, cache read/write, data helpers
scheduler.py     — APScheduler background refresh (every 15 min)
templates/       — Jinja2 HTML templates
data/cache.json  — Runtime cache (gitignored)
planning/        — Planning docs (ignore)
```

## Routes (current)
| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Home — word of day, daily sentence, weak words |
| GET | `/reader` | Fog-reveal reading passages |
| GET | `/vocab` | Flashcard session |
| POST | `/vocab/record` | Record flashcard miss/pass |
| GET/POST | `/phrasebook` | Phrase book (add, view) |
| POST | `/phrasebook/<id>/edit` | Edit a phrase |
| POST | `/phrasebook/<id>/delete` | Delete a phrase |
| GET | `/phrasebook/export` | Download CSV |

---

## What's Already Working ✅
- App renamed to **Estudio Abroad** (README says so, verify in templates)
- Daily sentence (ES + EN) fetched and cached
- Word of day: `es`, `en`, `definition`, `phonetic`, `example_es`, `example_en` all stored in cache
- Weak words ranked by `miss_count` descending (`get_weak_words()` in fetcher.py)
- Flashcard deck with 10 seed cards; misses recorded to `weak_words` in cache
- Phrase book: add, edit, delete, export CSV — all working
- Translation caching via SHA-256 keyed `cache["translations"]`
- Last refresh formatted as `2026-06-03 10:25 AM CST` via `format_refresh_time()` in fetcher.py
- APScheduler background refresh every 15 min (no manual refresh button)
- Footer signature: "Created by and for Xander McKie" linking to https://github.com/xandermckie

---

## What Still Needs Work ❌

### 1. Daily Word display (index.html)
The `word_of_day` data is complete in the cache (`es`, `phonetic`, `definition`, `example_es`) but the template is not displaying it correctly. Fix the template to:
- Show `word_of_day.es` prominently (large bold heading)
- Show pronunciation: `word_of_day.phonetic`
- Show English meaning: `word_of_day.en`
- Show example sentence in Spanish: `word_of_day.example_es`

### 2. Daily Sentence display (index.html)
- Show `daily_sentence.es` as the primary text
- English (`daily_sentence.en`) should only appear on hover (consistent with site-wide reveal behavior)

### 3. Site-wide Spanish-first hover reveal
Every piece of English text on the site should be hidden by default and revealed on cursor hover.
- Implement as a CSS/JS utility class (e.g., `.reveal-on-hover`) applied globally
- **Exception:** Do NOT apply to flashcard cards (`/vocab`) or any quiz UI — the challenge must remain intact

### 4. Weak Words section (index.html)
- Render the `weak_words` list passed from `get_homepage()`
- Display ranked by `miss_count` descending (fetcher already sorts this)
- Show ES word, EN meaning, miss count
- If list is empty, show a placeholder: e.g. "Complete some flashcards to see your weak words here."

### 5. Remove Quiz page
- There is no quiz route in `app.py` currently, but check all templates for any nav links or references to a quiz/cuestionario page and remove them

### 6. Footer cleanup (index.html / base template)
- Remove Quick Links section from the landing page footer
- Keep "Last Cache Refresh" — already formatted correctly via `homepage.last_refresh_display`
- Signature line should read: `Created by and for` **[Xander McKie](https://github.com/xandermckie)**

---

## Key Decisions Made
- Phrase book persists in `data/cache.json` under `cache["phrasebook"]` — same mechanism as all other cached data
- No standalone refresh button anywhere — browser refresh only
- Export CSV button lives on the `/phrasebook` page (already implemented in route)
- Translation rate limiting: MyMemory free tier allows ~1000 words/day unauthenticated; set `MYMEMORY_EMAIL` env var to raise limit to 10K/day. All calls go through `fetch_translation()` which checks cache first — never call the API directly
- Background scheduler runs `run_refresh()` in `scheduler.py` every 15 minutes

---

## Next Steps (in order)
1. Fix `index.html` — Daily Word display
2. Fix `index.html` — Daily Sentence display  
3. Implement site-wide hover reveal CSS/JS (skip flashcard pages)
4. Build out Weak Words section in `index.html`
5. Audit all templates for quiz nav links and remove
6. Clean up footer in base template

---

## Do Not Touch
- `fetch_translation()` logic in fetcher.py — caching is intentional
- `scheduler.py` — background refresh is working correctly
- `/phrasebook/export` route — already implemented
- `format_refresh_time()` — already correct format
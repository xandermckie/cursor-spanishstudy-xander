# Handoff — Estudio Abroad
*Generated: 2026-06-03*

## Session goal
Harden auth/vocab backend after user-account rollout: sequential flashcard sessions, session-fixation fix, request-scoped cache reads, legacy migration guard, and a pytest integration suite.

## Status
**Completed:**
- User auth (register/login/profile/avatar) committed on `main` — per-user JSON in `data/users/`
- Homepage UI: word of day, daily sentence, weak words, hover-reveal (`templates/index.html`)
- **Uncommitted (working):** vocab session state machine (`expected_index`, `visited_indices`); POST `/vocab/restart` with CSRF (replaces GET `?restart=1`); `_establish_session()` clears session on login/register; Flask `g`-scoped cache for global + user files; `get_user_nav_info()` for nav avatar; `get_homepage()` no longer inline-refreshes; dictionary API URL encoding; registration rollback if index save fails; legacy migration only when index empty + global cache has legacy keys
- **Tests:** `tests/` (11 tests) — all passing via `python -m pytest tests/ -q`

**In progress:**
- Four modified files + untracked `tests/`, `pytest.ini`, `requirements-dev.txt` — not committed

**Next action:**
- Review diff, commit the hardening + test suite, then push if desired

## Key decisions
- **Sequential vocab only:** Server tracks `expected_index`; client `next_i` URL param removed — prevents deck skip/cheat (`fetcher.record_flashcard_result`)
- **No inline refresh on homepage miss:** Scheduler owns API refresh; avoids request-thread blocking and duplicate API calls
- **Don't save on stats read:** `_compute_user_stats()` is read-only; `_ensure_user_stats()` only persists when defaults are backfilled
- **Session regeneration:** `_establish_session()` in `app.py:88` — mitigates session fixation after auth
- **Shared global cache + per-user files:** Translations/deck in `data/cache.json`; phrasebook/stats/vocab in `data/users/<uuid>.json` via `user_store.py`

## Tried and abandoned
- **GET `/vocab?restart=1`:** Replaced by POST `/vocab/restart` — restart must be CSRF-protected and login-required
- **Index-based vocab navigation (`?i=`):** Removed — caused skip-to-last-card exploit

## Critical context
- `app.py` — routes, `_establish_session`, `vocab_restart`, `_current_user_context` uses `fetcher.get_user_nav_info`
- `fetcher.py` — `_load_cache`/`_load_user_cache` (Flask `g` memoization), `get_vocab_session(user_id)` (no index arg), `record_flashcard_result` validation
- `user_store.py` — `_global_cache_has_legacy_user_data()`, registration rollback on index failure
- `templates/vocab.html` — restart is POST form with CSRF
- `tests/conftest.py` — tmp data dir, fake translations, `SCHEDULER_ENABLED=false`
- Env: `SECRET_KEY` required when `FLASK_DEBUG=0`; optional `MYMEMORY_EMAIL`, `NEWSAPI_KEY`
- Deploy: Render + gunicorn; demo URL in README

## Open questions
- Commit message scope: one commit for hardening + tests, or split?
- `cursorhandoff.md` describes a full Duolingo-style redesign — not started in code; reference only
- `notes/self-review.md` documents 32 deferred items (cache locking, `/travel` CSRF, etc.)

## Resume instruction
Continue from uncommitted backend hardening — review `git diff`, run `python -m pytest tests/ -q`, then commit the four modified files plus `tests/`, `pytest.ini`, and `requirements-dev.txt`. Start by reading `fetcher.py` (`record_flashcard_result`, `get_vocab_session`) and `tests/test_vocab.py`.

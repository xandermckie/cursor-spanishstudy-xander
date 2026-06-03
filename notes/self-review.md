# Self-Review — Estudio Abroad

## Summary

| Metric | Count |
|--------|------:|
| Files reviewed | 24 |
| Issues flagged | 42 |
| Fixed | 10 |
| Not fixed (documented) | 32 |

Review covered production Python, config, templates, and static assets. `_prototype/`, planning docs, and zip artifacts were excluded. `scripts/build_seeds.py` received a brief note only.

---

## Findings by file

### app.py

#### Issue: Default `SECRET_KEY` (`dev-change-me`) when env unset
- **Severity:** security
- **Decision:** fixed
- **Reasoning:** Weak session signing in production. App now raises `RuntimeError` at startup when `FLASK_DEBUG=0` and `SECRET_KEY` is missing or still the default. Local dev with `FLASK_DEBUG=1` keeps the default.

#### Issue: No CSRF protection on POST routes
- **Severity:** security
- **Decision:** fixed
- **Reasoning:** Forged cross-site requests could mutate phrasebook or vocab stats. Added session-based CSRF tokens via `generate_csrf_token()` / `validate_csrf()` and hidden fields on phrasebook and vocab forms.

#### Issue: `vocab_record` trusts client `es`, `en`, `index`, `missed`
- **Severity:** security
- **Decision:** fixed (server-side in `fetcher.record_flashcard_result`)
- **Reasoning:** Attackers could inflate XP and weak-word stats. Backend now verifies index and card content against the deck.

#### Issue: `phrasebook_edit` missing 500-char limit (add path had it)
- **Severity:** security / reliability
- **Decision:** fixed
- **Reasoning:** Unbounded input could bloat cache and hammer translation API. Edit route and `update_phrase()` now enforce `PHRASE_MAX_LENGTH`.

#### Issue: `REFRESH_INTERVAL_MINUTES` invalid value crashes startup
- **Severity:** reliability
- **Decision:** fixed
- **Reasoning:** Bad env var caused `ValueError`. `_parse_refresh_interval_minutes()` falls back to 15 with a warning.

#### Issue: `vocab_record` calls `get_vocab_session` outside try block
- **Severity:** reliability
- **Decision:** fixed
- **Reasoning:** Secondary failure after a primary error could 500. Redirect logic is now inside the try/except.

#### Issue: Broad `except Exception` on every route
- **Severity:** reliability
- **Decision:** not fixed
- **Reasoning:** Intentional fault tolerance (commit `5b6ed84`). Routes degrade to empty fallbacks and log exceptions rather than exposing stack traces.

#### Issue: Duplicate cache bootstrap (`ensure_cache_file` vs fetcher)
- **Severity:** reliability
- **Decision:** not fixed
- **Reasoning:** Both only create `{}` if missing; no conflicting writes. Low risk for a single-user app.

#### Issue: `/travel` POST has no CSRF
- **Severity:** security (low)
- **Decision:** not fixed
- **Reasoning:** POST only applies search filters; no persistent mutation. GET accepts the same params via `request.values`.

---

### fetcher.py

#### Issue: `cache.json` read-modify-write without locking
- **Severity:** reliability
- **Decision:** not fixed (partial mitigation)
- **Reasoning:** Concurrent web requests and the scheduler can still race. Full file locking or a database is out of scope; atomic writes reduce torn-file risk but not lost updates. Deferred to README “What I'd Build Next.”

#### Issue: Direct overwrite of `cache.json` on save
- **Severity:** reliability
- **Decision:** fixed
- **Reasoning:** Crash mid-write could corrupt the file. `_save_cache` now writes to `.json.tmp` and atomically replaces.

#### Issue: Corrupt cache silently becomes `{}`
- **Severity:** reliability
- **Decision:** fixed
- **Reasoning:** Data loss was invisible. `_load_cache` now logs JSON decode and OS errors separately.

#### Issue: `record_flashcard_result` does not verify deck card
- **Severity:** security
- **Decision:** fixed
- **Reasoning:** See app.py vocab integrity issue.

#### Issue: `update_phrase` no max length
- **Severity:** security
- **Decision:** fixed
- **Reasoning:** See phrasebook edit issue.

#### Issue: CSV export formula injection (`=`, `+`, `-`, `@`)
- **Severity:** security
- **Decision:** fixed
- **Reasoning:** Excel can execute formula cells. `_csv_cell()` prefixes risky values with `'`.

#### Issue: News article URLs not scheme-validated
- **Severity:** security
- **Decision:** fixed
- **Reasoning:** Malicious `javascript:` URLs in API data could execute on click. `_safe_https_url()` drops non-HTTPS links in `_parse_news_api_articles`.

#### Issue: NewsAPI key in query string
- **Severity:** security
- **Decision:** not fixed
- **Reasoning:** NewsAPI requires `apiKey` as a query parameter; cannot move to headers per their API.

#### Issue: `get_user_stats` writes cache on every read
- **Severity:** reliability
- **Decision:** not fixed
- **Reasoning:** Side effect ensures defaults exist; low impact for single-user usage and amplifies races only slightly.

#### Issue: Broad `except Exception` returning empty defaults
- **Severity:** reliability
- **Decision:** not fixed
- **Reasoning:** Matches app-level fault-tolerance strategy; keeps pages usable when cache or API fails.

#### Issue: `_homepage_from_cache` sets misleading `error` flag
- **Severity:** reliability
- **Decision:** not fixed
- **Reasoning:** UI behavior issue, not security; would need template/logic audit beyond review window.

---

### scheduler.py

#### Issue: Scheduled refresh races with web handlers on cache
- **Severity:** reliability
- **Decision:** not fixed
- **Reasoning:** Same as fetcher cache locking; acceptable for personal single-user app.

#### Issue: `atexit` shutdown with `wait=False`
- **Severity:** reliability
- **Decision:** not fixed
- **Reasoning:** Rare edge on process exit; atomic writes mitigate partial writes.

#### Issue: Broad `except Exception` on scheduled refresh
- **Severity:** reliability
- **Decision:** not fixed
- **Reasoning:** Job should not crash the scheduler; failure is logged.

#### Issue: Werkzeug reloader guard for debug mode
- **Severity:** reliability
- **Decision:** not fixed (positive finding)
- **Reasoning:** Correctly prevents double scheduler in debug; no change needed.

---

### fetcher_travel.py

#### Issue: Filter params not allowlisted
- **Severity:** security
- **Decision:** not fixed
- **Reasoning:** Arbitrary strings only affect matching; no match returns fallback recommendations. No injection surface.

#### Issue: Static seed data only
- **Severity:** style
- **Decision:** not fixed
- **Reasoning:** No bugs identified; file is appropriate for its role.

---

### fetcher_seeds.py

#### Issue: Large monolithic data file (~400 lines)
- **Severity:** style
- **Decision:** not fixed
- **Reasoning:** Data file, not logic; splitting is a refactor with no user-facing benefit.

---

### scripts/build_seeds.py

#### Issue: Non-atomic overwrite of `fetcher_seeds.py`
- **Severity:** reliability
- **Decision:** not fixed
- **Reasoning:** Dev-only generator, not used at runtime. Out of production review scope.

---

### requirements.txt, Procfile, render.yaml, .env.example

#### Issue: No Flask-WTF / explicit CSRF dependency
- **Severity:** style
- **Decision:** fixed via lightweight session CSRF in app.py
- **Reasoning:** Avoided new dependency; session tokens sufficient for this app.

#### Issue: `render.yaml` generates `SECRET_KEY` but does not set `NEWS_API_KEY`
- **Severity:** reliability
- **Decision:** not fixed
- **Reasoning:** News is optional; app handles missing key with a user-facing message. Documented in README.

---

### templates/base.html

#### Issue: Reader fog script is mouse-only
- **Severity:** reliability (accessibility)
- **Decision:** not fixed
- **Reasoning:** Real a11y gap but needs new keyboard/toggle UX for the fog lens — too large for this review window.

#### Issue: Inline `<script>` blocks
- **Severity:** style / security (CSP)
- **Decision:** not fixed
- **Reasoning:** Moving all inline JS to static files is a large refactor; no current XSS from these scripts.

#### Issue: Third-party Google Fonts without SRI
- **Severity:** security (low)
- **Decision:** not fixed
- **Reasoning:** Standard CDN pattern; SRI on dynamic font CSS is impractical.

#### Issue: Flash messages unfiltered
- **Severity:** security (low)
- **Decision:** not fixed
- **Reasoning:** All flash strings are hardcoded Spanish in `app.py`; Jinja auto-escapes output.

---

### templates/phrasebook.html

#### Issue: POST forms without CSRF
- **Severity:** security
- **Decision:** fixed
- **Reasoning:** Added hidden `csrf_token` on add, edit, and delete forms.

#### Issue: Edit input missing `maxlength="500"`
- **Severity:** reliability
- **Decision:** fixed
- **Reasoning:** Matches add form and server validation.

#### Issue: Inline `onsubmit` confirm handler
- **Severity:** style
- **Decision:** not fixed
- **Reasoning:** Works correctly; moving to static JS is cosmetic.

#### Issue: Edit toggle lacks `aria-expanded`
- **Severity:** style (accessibility)
- **Decision:** not fixed
- **Reasoning:** A11y polish, not security/reliability.

---

### templates/vocab.html

#### Issue: POST form without CSRF
- **Severity:** security
- **Decision:** fixed

#### Issue: Client-controlled hidden fields
- **Severity:** security
- **Decision:** fixed (backend validation)
- **Reasoning:** Hidden fields remain for UX but server verifies against deck.

#### Issue: English answer visible in HTML source before reveal
- **Severity:** style
- **Decision:** not fixed
- **Reasoning:** Flashcard UX tradeoff; not XSS. Challenge mode expects DOM presence for JS reveal.

---

### templates/travel.html

#### Issue: POST form without CSRF
- **Severity:** security (low)
- **Decision:** not fixed
- **Reasoning:** Search-only; no persistent state change.

#### Issue: Leaflet loaded from unpkg with SRI on script
- **Severity:** security (low)
- **Decision:** not fixed (positive finding)
- **Reasoning:** Script has integrity attribute; acceptable CDN use.

---

### templates/news.html

#### Issue: External `article.url` in `href`
- **Severity:** security
- **Decision:** fixed (server-side in fetcher)
- **Reasoning:** HTTPS-only URLs before render.

---

### templates/reader.html

#### Issue: Mouse-only fog interaction
- **Severity:** reliability (accessibility)
- **Decision:** not fixed
- **Reasoning:** Core feature design; keyboard alternative is a feature project.

#### Issue: Duplicate ResizeObserver logic vs base.html
- **Severity:** style
- **Decision:** not fixed
- **Reasoning:** Maintainability only; no user-facing bug.

#### Issue: `weak-word-item` not keyboard-operable
- **Severity:** reliability (accessibility)
- **Decision:** not fixed
- **Reasoning:** Would need tabindex/keydown in `reveal.js`.

---

### templates/history.html

#### Issue: Tab buttons missing full WAI-ARIA tabs pattern
- **Severity:** style (accessibility)
- **Decision:** not fixed
- **Reasoning:** A11y polish; tabs still work with click.

#### Issue: Inline tab script
- **Severity:** style
- **Decision:** not fixed
- **Reasoning:** CSP/maintainability preference.

---

### templates/index.html

#### Issue: `weak-word-item` keyboard gap
- **Severity:** reliability (accessibility)
- **Decision:** not fixed
- **Reasoning:** Same as reader.html weak-word items.

#### Issue: Duplicated reveal markup for word of the day
- **Severity:** style
- **Decision:** not fixed
- **Reasoning:** Could use `reveal_card` macro; cosmetic consistency only.

---

### templates/resources.html

#### Issue: External resource URLs in `href`
- **Severity:** security (low)
- **Decision:** not fixed
- **Reasoning:** Static curated seed URLs today; all HTTPS. Would add `_safe_https_url` if data source becomes dynamic.

---

### templates/partials/reveal_card.html, pez.html, section_alerts.html

#### Issue: None significant
- **Severity:** n/a
- **Decision:** not fixed
- **Reasoning:** Static macros and fixed strings; Jinja escaping in place.

---

### static/js/theme.js

#### Issue: None significant
- **Severity:** n/a
- **Decision:** not fixed
- **Reasoning:** Uses `textContent` and `localStorage`; no `innerHTML` with user data.

---

### static/js/reveal.js

#### Issue: `weak-word-item` click-only (no keyboard)
- **Severity:** reliability (accessibility)
- **Decision:** not fixed
- **Reasoning:** `.reveal-card` has keyboard support; weak-word items would need parity.

---

### static/js/vocab.js

#### Issue: `innerHTML` for celebration overlay
- **Severity:** style
- **Decision:** not fixed
- **Reasoning:** Static HTML string only; no user data. Prefer `createElement` for consistency but not a security risk.

#### Issue: 1.8s delayed submit on correct answer
- **Severity:** reliability (low)
- **Decision:** not fixed
- **Reasoning:** Minor double-click edge case; intentional celebration UX.

---

### static/css/estudio.css

#### Issue: None significant
- **Severity:** n/a
- **Decision:** not fixed
- **Reasoning:** Presentation layer only; no security or reliability concerns.

---

## Commits

- `Fix: address security and reliability issues from self-review` — CSRF, SECRET_KEY guard, vocab validation, phrasebook limits, atomic cache writes, CSV sanitization, HTTPS news URLs, env parsing, vocab route try/except
- `Docs: add self-review notes from final code review` — this file

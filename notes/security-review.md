# Security Review — Estudio Abroad

Audit date: 2026-06-08. Automated scans + manual checklist per the security hardening plan.

## Executive summary

| Area | Pre-fix risk | Post-fix status |
|------|--------------|-----------------|
| Hardcoded secrets | Low | Pass — env-only; production `SECRET_KEY` required |
| Password storage | Low | Pass — Werkzeug hash + Fernet at rest |
| SQL injection | None | N/A — no database |
| XSS | Low–Medium | Pass — Jinja escaping; CSP + headers added |
| Auth bypass | Low | Pass — server-side enforcement |
| Client auth logic | Low | Pass — UX-only gates |
| Supply chain | Medium | Mitigated — deps bumped; `pip-audit` in CI |
| Abuse / DoS | Medium | Mitigated — rate limits on auth + translation |

---

## Findings table

| ID | Severity | Location | Issue | Exploit scenario | Recommendation | Status |
|----|----------|----------|-------|------------------|----------------|--------|
| S-01 | P1 | `app.py` | No session cookie hardening | Session cookie readable via XSS or sent over HTTP | Set `HTTPONLY`, `SAMESITE=Lax`, `SECURE` in prod | **Fixed** |
| S-02 | P1 | `app.py` `/travel` POST | Missing CSRF | Cross-site POST triggers Google Places API calls | Add CSRF validation + hidden field | **Fixed** |
| S-03 | P1 | `app.py` `/login`, `/register` | No rate limiting | Brute-force password guessing | Flask-Limiter 10/min per IP | **Fixed** |
| S-04 | P1 | `app.py` | Ephemeral `SECRET_KEY` when unset in prod | Sessions and derived encryption reset every deploy | Fail fast if `SECRET_KEY` missing in prod | **Fixed** |
| S-05 | P1 | `app.py` | No security response headers | Clickjacking, MIME sniffing | `X-Frame-Options`, `nosniff`, CSP, Referrer-Policy | **Fixed** |
| S-06 | P1 | `/translate/api`, `/voice/translate` | Unauthenticated translation proxy | Attacker exhausts third-party API quotas | Rate limit 30/min per IP | **Fixed** |
| S-07 | P2 | `requirements.txt` | CVEs in Flask, dotenv, requests, cryptography | Known library vulnerabilities | Bump to patched versions | **Fixed** |
| S-08 | P2 | `templates/travel.html` | `GOOGLE_MAPS_API_KEY` client-visible | Key abuse if unrestricted in Google Cloud | Document referrer restrictions in README | **Documented** |
| S-09 | P2 | `static/js/voice-whisper.js` | CDN dynamic import without SRI | Supply-chain swap of Transformers.js | Version pinned; CSP allows jsdelivr only | **Mitigated** |
| S-10 | P2 | `estudioabroad.zip` | Binary archive in repo | Possible embedded secrets | Added to `.gitignore` | **Fixed** |
| S-11 | P3 | File JSON storage | RMW races without locking | Concurrent writes corrupt data | Deferred — needs DB or file locking | Open |
| S-12 | P3 | `encryption.py` | `ENCRYPTION_KEY` derived from `SECRET_KEY` | Key rotation couples session + data encryption | Document; use dedicated `ENCRYPTION_KEY` in prod | Documented |

---

## Automated scan results

### Secret pattern grep

```
rg -i "(api[_-]?key|secret|password|token|bearer)\s*=\s*['\"][^'\"]+['\"]" --glob '!tests/**'
```

**Result:** No hardcoded credentials in application code. Test fixtures in `tests/conftest.py` use placeholder keys only.

### Command injection / eval

**Result:** No `subprocess`, `os.system`, `shell=True`, `eval()`, or `exec()` in codebase.

### Jinja XSS surface

**Result:** No `|safe`, `Markup()`, or `{% autoescape off %}`. User phrases rendered via `{{ es }}` / `{{ en }}` (auto-escaped).

### pip-audit (pre-fix)

| Package | Version | CVE | Fix version |
|---------|---------|-----|---------------|
| flask | 3.1.0 | CVE-2025-47278, CVE-2026-27205 | 3.1.3 |
| python-dotenv | 1.0.1 | CVE-2026-28684 | 1.2.2 |
| requests | 2.32.3 | CVE-2024-47081, CVE-2026-25645 | 2.33.0 |
| cryptography | 43.0.0 | Multiple (OpenSSL, name constraints) | 46.0.7 |

---

## Checklist pass/fail (pre-fix baseline)

| Check | Result |
|-------|--------|
| Secrets from environment only | Pass |
| `.env` gitignored | Pass |
| Password hashing (Werkzeug) | Pass |
| Fernet encryption at rest | Pass |
| Session regeneration on login | Pass |
| CSRF on mutating routes | Fail — `/travel` POST |
| Server-side auth boundary | Pass |
| Vocab anti-cheat server validation | Pass |
| SQL injection | N/A |
| Path traversal on user_id | Pass — SHA-256 hex IDs |
| CSV formula injection guard | Pass |
| Open redirect guard | Pass |
| Rate limiting | Fail |
| Security headers | Fail |
| Dependency CVE monitoring | Fail — no CI |

---

## Remediation implemented

1. Session cookie hardening in `create_app()`
2. CSRF on `POST /travel`
3. Flask-Limiter on auth (10/min) and translation APIs (30/min)
4. Production `SECRET_KEY` guard (raises on missing/default)
5. Security response headers via `after_request`
6. Dependency version bumps in `requirements.txt`
7. `tests/test_security.py` — cookies, CSRF, headers, auth boundaries, rate limits
8. `.github/workflows/security.yml` — pip-audit, gitleaks, pytest
9. README production security checklist

Optional env flag `TRANSLATION_REQUIRES_AUTH=1` requires login for `/translate/api` and `/voice/translate` in production.

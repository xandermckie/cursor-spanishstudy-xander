# Tool Map — Estudio Abroad (Week of Jun 2026)

## Cursor

**What did Cursor do better than you expected?**

Multi-file changes in one shot: wheel nav replacing the old aquarium nav, profile encryption with tests, Wikipedia reader rotation, travel map + Google Places, vocab shuffle, homepage fixes. The self-review / full-review passes actually landed real fixes (CSRF, session clear on login, vocab anti-cheat, atomic cache writes). Faster than typing all of that by hand.

**What did it get wrong or mislead you on?**

Voice page: several Agent tries to fix listen/escuchar closing instantly. Still broken — ended up removing voice entirely and pushing that. Travel map at first showed the same recommendations no matter what filters you picked until a follow-up session. Burning through usage limits because I attached a bunch of Claude skills to Cursor and ran Plan → full Agent implement loops all day Thursday.

**Which interaction mode did you use most? Why?**

Agent panel, almost exclusively. This app is Flask + templates + JS in different files — Tab and Inline Edit are too small for "fix travel map + fetcher + template." Pattern this week: describe the issue → Plan mode → "implement the plan" → review diff → commit.

**What would you set up differently in `.cursor/rules/` if you started over?**

This repo has no project rules — everything lives in global Cursor rules (security, TypeScript, React stuff that doesn't apply here). I'd add a slim `.cursor/rules/` for Estudio only: Python/Flask stack, `data/` paths, `ENCRYPTION_KEY` + `SECRET_KEY` env notes, run tests with `python -m pytest tests/ -q`, scope changes to the file I @ mention, and don't rip out features without asking (voice lesson learned). Skip duplicating the long global rule set.

---

## Cursor vs. Claude Chat vs. Cowork

**Concrete example this week**

Voice page not working — click Escuchar, modal closes, no time to speak. Used **Cursor Agent** to debug `voice.js`, wheel-nav conflicts, session handling. Right tool for touching code; wrong outcome — still broken after fixes. I told Agent to remove voice completely and commit/push. **Chat** would've explained Web Speech API / browser permissions but wouldn't have edited the repo. **Cowork** doesn't fit how I work — I want to see and accept every file change.

**New project tomorrow — tool workflow**

Brief spec in Chat if I need wording help, then **Cursor Agent** for all implementation, tests, and README. Review diffs before commit. Keep skills minimal per project so I don't eat the whole quota on one week. Cowork only if I had a non-code task; for apps, Cursor wins because I can interact with every change.

I prefer Cursor over Chat and Cowork because I like stepping through implementations line by line. Porting Claude skills into Cursor improved prompt quality but definitely hurt my usage limits.

---

## The code I built

**Most proud of**

Wheel navigation (`static/js/wheel-nav.js` + `base.html`) — biggest UX swing on the project and it actually shipped. Close second: user accounts with per-user JSON, Fernet encryption on profile cache, and vocab session rules (`expected_index`, CSRF restart) from the hardening pass.

**Most want to rewrite**

`fetcher.py` — too much in one file (cache, APIs, vocab, stats, travel hooks). JSON read-modify-write on disk with no locking is fine for a demo but I'd split modules or move to a DB before calling it production. Inline JS scattered in templates vs one static bundle is another cleanup pass.

**A line I didn't fully understand — then I did**

`fetcher.py` line 794: `card = deck[index]` inside `record_flashcard_result`.

I added shuffle this week. `get_vocab_session` maps session position through `shuffled_order` — e.g. position `0` might show `deck[5]`. But `record_flashcard_result` still checks the submitted `es`/`en` against `deck[index]` where `index` is the session step (0, 1, 2…), not the deck slot. So after shuffle, validation can reject the correct card the UI just showed. **Now I get it:** `index` in the form is "which card in today's shuffled run," not "which index in the master deck." Line 794 should use `deck[session["shuffled_order"][index]]` (same mapping as lines 736–738). I hadn't hit it in manual testing yet; reading both functions side by side made the mismatch obvious.

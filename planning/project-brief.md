## What I'm Building

Estudio Personal is a personal language study app built specifically for studying abroad in Barcelona. It's a custom Duolingo alternative that teaches you the Spanish and Catalan you'll actually need — transit vocab, restaurant phrases, market interactions, emergency language. The core mechanic is a fog-reveal reader: you read passages in Spanish or Catalan with English translations hidden underneath, revealed by a circular lens that follows your cursor as you hover. Beyond the reader, the app tracks weak areas across vocab categories (transit, food, places, phrases, emergencies), serves up daily challenge sentences, lets you build a personal phrasebook, and quizzes you on what you've studied. Everything is cached and served from JSON — no database, no backend complexity.

## Who It's For

Just me. I'm leaving for Barcelona in summer 2026 and want to arrive fluent in practical, everyday language rather than the textbook stuff. I need an app that mirrors my learning style (reading in context, understanding from inference when possible, revealing translations on demand) and is designed around the specific vocab gaps I know I have. Generic Duolingo doesn't do that.

## The API

**Primary APIs:**

1. **MyMemory (Google Translate backend)**
   - Base URL: `https://api.mymemory.translated.net/get`
   - Authentication method: None (optional email for higher limits)
   - Rate limits: 5000 requests/day, 375/hour per IP
   - What data I'll be pulling: Translations ES/CA ↔ EN, example segments from translation memory
   - Link to docs: https://mymemory.translated.net/

2. **Glosbe**
   - Base URL: `https://glosbe.com/gapi/v0.1/translate`
   - Authentication method: None
   - Rate limits: Generous, no formal limit documented
   - What data I'll be pulling: Bilingual example sentences in context (Spanish-English, Catalan-English)
   - Link to docs: https://glosbe.com/

3. **DictionaryAPI.dev**
   - Base URL: `https://api.dictionaryapi.dev/api/v2/entries/en/`
   - Authentication method: None
   - Rate limits: No strict limit, reasonable use
   - What data I'll be pulling: English definitions, phonetics, usage examples
   - Link to docs: https://dictionaryapi.dev/

4. **Open Trivia DB**
   - Base URL: `https://opentdb.com/api.php`
   - Authentication method: None
   - Rate limits: No authentication required, reasonable use
   - What data I'll be pulling: Multiple choice quiz questions (can filter by category, difficulty)
   - Link to docs: https://opentdb.com/api_config.php

5. **Lingua Robot (optional)**
   - Base URL: `https://www.lingua-robot.com/api/v1/`
   - Authentication method: None
   - What data I'll be pulling: Verb conjugation and morphology for Spanish/Catalan
   - Link to docs: https://www.lingua-robot.com/api/documentation/

## Data I'm Storing

**What gets cached:**
- Translated vocab entries (word, translation, example sentences) — one JSON file per category
- User's personal phrasebook entries
- Quiz history (what the user got right/wrong, by category and date)
- Weak area tracker (counts of incorrect answers per vocab category)
- Daily sentence seed (today's featured passage for the fog-reveal reader)

**How often it refreshes:**
- Vocab translations: every 6 hours via APScheduler (background job)
- Daily sentence: once per day at app startup or manual `/refresh` trigger
- Phrasebook & history: on-demand (write on form submission, read on page load)
- Quiz questions: fresh pull from Open Trivia DB each time user starts a quiz

**File format:**
- JSON (all data)

**Example structure for a vocab entry:**
```json
{
  "category": "transit",
  "entries": [
    {
      "es": "¿A qué hora sale el próximo metro?",
      "ca": "A quina hora surt el pròxim metro?",
      "en": "What time does the next metro leave?",
      "context": "Example sentence from Glosbe showing usage",
      "weak_count": 2,
      "last_seen": "2026-01-15T14:32:00Z"
    }
  ]
}
```

## User Interactions

- **Hover over the fog-reveal reader** — cursor grows into a circle, English translation shows through the circular lens as you move, creates an exploration feeling rather than a drill feeling
- **Click vocab category tabs** — filters the vocab list to show only phrases from that category (transit, food, places, phrases, emergencies)
- **Click a vocab card** — flips it to reveal English translation and example usage
- **Add a phrase** — form on /phrasebook to enter Spanish, Catalan, English, and pick a category; submitted phrases are stored and immediately available in quizzes
- **Take a quiz** — click start quiz, answer multiple choice questions (mix of personal vocab + Open Trivia DB questions), see score and which categories you're weakest in
- **View weak areas dashboard** — on homepage, see a ranked list of your weakest categories by % correct over your last 10 attempts, click to drill that category
- **Manually refresh data** — click "refresh cache" button to pull fresh translations and daily sentence
- **Export phrasebook** — download a CSV of your personal phrases + vocab for studying offline or importing elsewhere

## Pages / Routes

- GET `/` → dashboard: weak areas summary, today's fog-reveal sentence challenge, quick-access category buttons, stats (total vocab, quiz attempts, accuracy by category)
- GET `/reader` → full fog-reveal reader with either a pre-written passage or today's featured sentence; language selector (Spanish or Catalan); optional difficulty toggle
- GET `/vocab` → vocab browser filtered by category; cards show Spanish/Catalan front, English on hover; embedded example sentences from Glosbe
- GET `/vocab/<category>` → same vocab view but filtered to one category (e.g., `/vocab/transit`)
- GET `/phrasebook` → display user's personal phrasebook entries organized by category; each shows date added
- POST `/phrasebook` → form submission handler; validates input, stores to JSON, returns success/error
- DELETE `/phrasebook/<id>` → remove a phrase (AJAX or form)
- GET `/quiz` → quiz page; shows question, 4 multiple choice answers, timer, progress bar; mixes Open Trivia DB + user vocab
- POST `/quiz/submit` → handles answer submission, logs to history, calculates accuracy
- GET `/quiz/results` → shows quiz recap, score, breakdown by category, weakest categories highlighted
- GET `/refresh` → manually trigger background refresh of all API caches; returns status message
- GET `/export` → generates and downloads phrasebook + vocab as CSV

## Error States

- **MyMemory/Glosbe API is down or slow** → fall back to cached translations and MyMemory TM matches; show subtle warning banner; don't crash the reader
- **Open Trivia DB returns no questions matching the filter** → fall back to user's personal vocab for quiz questions; if no personal vocab exists either, show "not enough questions yet, try adding phrases first" message
- **User's JSON cache file is corrupted or missing** → seed with default empty structure on app startup; log the error; don't show stack trace to user
- **User submits empty phrasebook form** → validate on submit, show inline error "all fields required," don't add to JSON
- **Network timeout on any API call** → catch after 3 seconds, log to console, use cached version if available, show "slow connection" warning banner (non-blocking, dismissible)
- **User clicks "refresh" but all APIs are down** → show "refresh failed, using cached data" message; don't block the page

## Stretch Goals

- **Audio pronunciation** — integrate Forvo API to play native speaker audio for any vocab word (Catalan especially, since it's less common)
- **Spaced repetition** — track which words you see often vs. rarely; surface weak words more frequently in quizzes and the daily sentence rotation
- **Sentence difficulty slider** — let user filter reader passages by complexity (A1/A2/B1/B2 CEFR levels) using sentence length + vocabulary overlap as a proxy
- **Share mode** — generate a shareable link to your phrasebook or a quiz challenge for a friend also studying Spanish
- **Offline mode** — service worker + localStorage so the app works without internet (using cached data only)
- **Dark/light theme toggle** — currently locked to dark theme, add a toggle that respects `prefers-color-scheme`
- **Analytics dashboard** — track learning velocity: words learned per day, quiz improvement over time, time spent on reader, heatmap of weak categories

Great — before I craft the prompt, let me fill in the gaps so Cursor has everything it needs. Based on what you wrote, here are my questions:Got everything I need. Here's your polished Cursor prompt:

---

**You are a senior full-stack engineer working on a Flask web application called Estudio Abroad** — a Spanish learning tool for senior college students studying abroad in Barcelona. The app uses LibreTranslate and Google Translate API for translations and caches data to stay below API rate limits. Keep all existing rate-limiting and caching best practices in place, and extend them to any new translation calls you add.

**Make the following changes. Work feature by feature, and do light cleanup on any code you touch:**

**1. Rename & rebrand**
- Change the app name from "Estudio Personal" to "Estudio Abroad" everywhere (title, nav, headings, metadata).

**2. Site-wide Spanish-first reveal behavior**
- All user-facing text should display in Spanish by default.
- English is revealed only on hover/cursor-over (tooltip or inline reveal — your choice, but it must be site-wide and consistent).
- **Exception:** Flash card sections and any quiz-style interactions should remain challenge-only — do not apply the reveal behavior there.

**3. Fix the Daily Word feature**
- Currently the word is not displayed in Spanish and lacks emphasis. Fix it to:
  - Show the Spanish word prominently (larger font or bold heading)
  - Include English meaning, pronunciation guide, and an example sentence using the word in context
- Add a **Daily Sentence** section in the same format directly below it.

**4. Build out the Weak Words section**
- Display words ranked by most frequent misses from the flashcard feature (descending).
- This list should update dynamically as flashcard session data is recorded.
- If no data exists yet, show a placeholder state.

**5. Remove the Quiz page**
- Delete the quiz page and all routes, nav links, and references to it entirely. It was not implemented correctly and will be rebuilt later.

**6. Build the Phrase Book**
- Users can input a word or phrase; it gets translated to Spanish via the existing translation API (cache results using the same mechanism already in use).
- The phrase book persists in the cache so users can return to it across sessions.
- Users can add, edit, and delete entries.
- Include an **Export to CSV** button directly on the phrase book page.
- Remove any standalone "Refresh" button — browser refresh handles this.

**7. Footer cleanup**
- Remove the Quick Links section from the bottom of the landing page.
- Keep the "Last Cache Refresh" timestamp but reformat it to: `2026-06-03 10:25 AM CST`
- Add a signature line at the very bottom: `Created by and for` **[Xander McKie](https://github.com/xandermckie)** — hyperlink the name to `https://github.com/xandermckie`.

**Constraints:**
- Do not break existing flashcard functionality.
- Do not introduce new translation API calls without caching — stay under rate limits.
- Keep all changes within the existing Flask + separate API architecture.
- If anything is ambiguous (e.g., the exact cache format or where phrase book data lives), ask one clarifying question before proceeding.

---

**What I changed and why:** Your original was a solid brain-dump but read like a stream of consciousness — Cursor would've tried to do everything at once and missed details. The rewrite groups changes by feature, leads with role + tech context so Cursor knows the constraints upfront, promotes the rate-limiting rule to a top-level requirement (not buried at the end), and adds the "ask one clarifying question" escape hatch so it doesn't silently make wrong assumptions about your cache format.

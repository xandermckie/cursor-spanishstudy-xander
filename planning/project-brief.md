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
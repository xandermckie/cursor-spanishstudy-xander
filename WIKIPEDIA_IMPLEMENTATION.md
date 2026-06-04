# Wikipedia Reader Integration - Implementation Summary

## Overview
Successfully integrated Spain-related Wikipedia articles into the reader page. Articles are fetched from the Spanish Wikipedia API, cached for 24 hours, and rotated daily alongside existing Barcelona-focused passages.

## Changes Made

### 1. Added Wikipedia Article Pool (`fetcher_seeds.py`)
- Added `WIKIPEDIA_ARTICLES_ES` list with 14 Spain-related topics:
  - Historia de España
  - Flamenco
  - Paella
  - Sagrada Família
  - Pablo Picasso
  - Miguel de Cervantes
  - Guerra Civil Española
  - Reconquista
  - Imperio español
  - Gaudí
  - Tapas
  - Semana Santa en España
  - La Tomatina
  - Real Madrid Club de Fútbol

### 2. Wikipedia Fetching Logic (`fetcher.py`)
- **`_fetch_wikipedia_article(title, lang="es")`**: Fetches article intro from Wikipedia API
  - Uses proper User-Agent header to avoid 403 errors
  - Extracts main introduction section (first 3 paragraphs)
  - Limits content to ~800-1500 characters for reading practice
  - Returns structured data with title, body, language, and source

- **`_ensure_wikipedia_passages(cache)`**: Manages Wikipedia article caching
  - Fetches all articles from the pool
  - Translates Spanish → English using existing MyMemory integration
  - Caches for 24 hours to minimize API calls
  - Called automatically by scheduler every 15 minutes

- **Updated `get_reader()`**: Combines seed passages + Wikipedia articles
  - Merges Barcelona-focused seed passages with Wikipedia content
  - Uses `_utc_day_index()` for daily rotation (based on day of year)
  - Returns one passage per day from the combined pool

- **Updated `run_refresh()`**: Added `_ensure_wikipedia_passages()` call
  - Wikipedia articles refresh automatically with other content
  - Integrated into existing 15-minute scheduler cycle

### 3. Reader Template Updates (`templates/reader.html`)
- Added Wikipedia source badge to article cards
- Shows "Wikipedia" label when `passage.source == 'wikipedia'`
- Maintains existing fog-reveal interaction for all passages

### 4. Documentation Updates (`README.md`)
- Updated feature description for Lector
- Added Wikipedia integration details to "How It Works" section
- Documented 24-hour cache refresh cycle

## Technical Details

### API Integration
- **Endpoint**: `https://es.wikipedia.org/w/api.php`
- **Parameters**:
  - `action=query`
  - `prop=extracts`
  - `exintro=True` (introduction only)
  - `explaintext=True` (plain text, no HTML)
- **Rate Limiting**: Cached for 24 hours per article
- **User-Agent**: "EstudioAbroadApp/1.0 (Spanish Learning App; educational use)"

### Content Processing
1. Fetch intro section from Wikipedia
2. Extract first 3 paragraphs
3. Trim to ~1200 characters at sentence boundary if needed
4. Translate to English via MyMemory API
5. Cache with metadata (title, body, translation, source)

### Daily Rotation
- Combined pool: 4 seed passages + ~14 Wikipedia articles = ~18 total
- Rotation index: `day_of_year % total_passages`
- Changes once per day at midnight UTC
- Deterministic (same article appears on same day globally)

## Testing
- ✅ All existing tests pass (37 tests)
- ✅ Wikipedia API fetch tested with 3 sample articles
- ✅ Flask app starts successfully with new features
- ✅ No linter errors introduced

## Benefits
1. **Longer content**: Wikipedia articles are typically 300-1200 characters vs seed passages (~200-400 chars)
2. **Cultural context**: Real Spain-related topics (history, culture, food, landmarks)
3. **Daily variety**: 18+ passages rotate daily (vs 4 static seed passages)
4. **Automatic updates**: Scheduler refreshes articles every 24 hours
5. **Minimal API usage**: Heavy caching + batch fetching during scheduled refresh

## Future Enhancements
- Add more Wikipedia topics (expand from 14 to 30+ for monthly rotation)
- Support multiple languages (Catalan Wikipedia articles)
- Add difficulty levels based on passage length/complexity
- User preference for passage categories (history, sports, culture, etc.)

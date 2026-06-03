# Estudio Abroad — Cursor Implementation Handoff

## Overview

This document provides everything needed to implement the new Estudio Abroad design in the existing Flask/Jinja2 codebase. The design shifts from a dark editorial aesthetic to a bright, playful, Duolingo/Mango-inspired language learning app with a custom fish mascot ("Pez"), gamification elements, and modern UI components.

**Live prototype:** See `Estudio Abroad.html` and its component files for the working interactive reference.

---

## Design System

### Colors

```css
:root {
  /* Primary palette */
  --primary: #FF6B35;
  --primary-dark: #E55A2B;
  --primary-light: #FFF0EB;
  --secondary: #FFB627;
  --secondary-light: #FFF8E7;
  
  /* Accents */
  --teal: #2EC4B6;
  --teal-light: #E8FAF8;
  --red: #E63946;
  --green: #22C55E;
  --green-light: #ECFDF5;
  
  /* Light mode */
  --bg: #FAFAF8;
  --surface: #FFFFFF;
  --surface-hover: #F9FAFB;
  --text: #1A1A2E;
  --text-secondary: #6B7280;
  --text-muted: #9CA3AF;
  --border: #E5E7EB;
  --border-light: #F3F4F6;
  
  /* Dark mode */
  --dark-bg: #0F1117;
  --dark-surface: #1A1D28;
  --dark-surface-2: #242736;
  --dark-text: #F0F0F5;
  --dark-text-secondary: #9CA3AF;
  --dark-border: #2D3042;
  
  /* Shadows */
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.1);
  
  /* Radii */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --radius-full: 9999px;
}
```

### Typography

**Fonts:** DM Sans (headings) + Plus Jakarta Sans (body). Both from Google Fonts.

```html
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
```

```css
--font-heading: 'DM Sans', 'Plus Jakarta Sans', system-ui, sans-serif;
--font-body: 'Plus Jakarta Sans', 'DM Sans', system-ui, sans-serif;
```

**Scale:**
| Element | Size | Weight | Family |
|---------|------|--------|--------|
| Page title (h1) | 24-28px | 800 | Heading |
| Section heading (h2) | 22px | 800 | Heading |
| Card title (h3) | 16-17px | 700 | Heading |
| Body text | 14-15px | 400-500 | Body |
| Small / label | 12-13px | 600 | Body |
| Stat numbers | 22px | 800 | Heading |

All headings use `letter-spacing: -0.02em`. Use `text-wrap: balance` on headings, `text-wrap: pretty` on paragraphs.

---

## Mascot: Pez

Pez is a blocky, cute red-and-yellow fish character. SVG-based, inline-rendered.

**Colors:**
- Body: `#E63946` (red)
- Belly stripe: `#FFB627` (yellow)
- Tail: `#FFB627` with `#F59E0B` connector
- Fins: `#FF8A65`
- Eye: white circle + `#1A1A2E` pupil + white shine dot
- Blush: `#FF8A65` at 50% opacity

**Expressions:** happy, excited, thinking, sleeping, wink, celebrating — controlled by eye scale, mouth curve, and blush visibility.

**Behavior:** Pez is a "chill guide" — appears in corners of pages, reacts subtly:
- Home: greeting with speech bubble, bobbing animation
- Reader: thinking expression while reading
- Vocab results: celebrating or thinking based on score
- Empty states: thinking with helpful speech bubble
- Footer: wink expression
- Travel: happy with search encouragement

**Implementation:** Create the SVG as a Jinja2 macro or a reusable `<svg>` partial. The full SVG source is in `mascot.jsx` — port it to a `templates/partials/pez.html` macro with parameters for `size`, `expression`, and `speech`.

**Bobbing animation:**
```css
@keyframes pezBob {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
.pez-animated { animation: pezBob 3s ease-in-out infinite; }
```

---

## Component Patterns

### Navbar
- **Position:** sticky top
- **Background:** `--surface` with bottom border `--border`
- **Height:** 60px
- **Layout:** Logo (Pez icon + "Estudio Abroad" in primary/800) left, text-only nav links right, dark mode toggle (circle button) far right
- **Active link:** `--primary-light` background, `--primary` text, weight 700
- **Inactive link:** `--text-secondary`, weight 500, hover → `#F3F4F6` bg
- **Mobile (< 900px):** hamburger menu, links stack vertically
- **Dark mode toggle:** 36px circle, shows ☀️/🌙

### Cards
- **Background:** `--surface`
- **Border:** `1px solid var(--border)`
- **Border-radius:** `--radius-lg` (16px)
- **Padding:** 24px default (varies by context)
- **Shadow:** `--shadow-sm`
- **Hover (interactive cards):** `--shadow-md` + `translateY(-2px)`
- **No decorative left borders or colored accents on cards themselves**

### Buttons
| Variant | Background | Text | Border | Hover |
|---------|-----------|------|--------|-------|
| Primary | `--primary` | white | none | `--primary-dark` |
| Secondary | `#F3F4F6` | `--text` | `--border` | `#E5E7EB` |
| Ghost | transparent | `--text` | none | `#F3F4F6` |
| Success | `--green` | white | none | `#16A34A` |
| Danger | `#FEF2F2` | `--red` | `#FECACA` | `#FEE2E2` |

All buttons: `border-radius: --radius-md`, `font-weight: 600`, sizes sm/md/lg (8-14px padding range).

### Badges
- Pill-shaped (`--radius-full`), 12px font, weight 700
- Color variants: primary (orange bg/text), teal, secondary (yellow), green, red — all use light bg + strong text

### Click-to-Reveal (Spanish → English)
This is the core learning mechanic. Replace the old `.click-reveal` pattern:

```html
<div class="reveal-card" onclick="this.classList.toggle('is-open')">
  <div class="reveal-es">Spanish text here</div>
  <div class="reveal-en">English translation here</div>
  <div class="reveal-hint">Tap to reveal English</div>
</div>
```

```css
.reveal-card {
  padding: 16px 20px;
  cursor: pointer;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  transition: all 0.25s ease;
}
.reveal-card.is-open {
  background: var(--primary-light);
  border-color: rgba(255, 107, 53, 0.25);
}
.reveal-es {
  font-size: 17px;
  font-weight: 600;
  color: var(--text);
}
.reveal-en {
  max-height: 0;
  opacity: 0;
  overflow: hidden;
  transition: all 0.3s ease;
  font-size: 15px;
  color: var(--teal);
  font-style: italic;
}
.reveal-card.is-open .reveal-en {
  max-height: 100px;
  opacity: 1;
  margin-top: 8px;
}
.reveal-hint {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
}
.reveal-card.is-open .reveal-hint { display: none; }
```

### Stat Cards
- Horizontal layout: 44px icon square (colored bg at 8% opacity) + value (22px/800) + label (12px/muted)
- Used in a 4-column responsive grid on home page

### XP Bar
- Track: 10px height, `#F3F4F6` background, full border-radius
- Fill: gradient from `--secondary` to `--primary`
- Label: "Level N" badge left, "120/200 XP" right in primary/700

### Streak Badge
- Pill: `--secondary-light` bg, 🔥 emoji + "N días" in `#B8860B`/800

---

## Page-by-Page Implementation Guide

### 1. Home (`/` → `index.html`)

**Layout (top to bottom):**
1. **Hero greeting** — Pez (64px, happy, speech bubble "¡Hola, Xander! Ready to learn?") + "Buenos días" h1 + subtitle
2. **Stats grid** — 4-column grid: streak, total XP, words learned, accuracy (StatCard components)
3. **XP Progress card** — "Daily Progress" header + StreakBadge + XPBar + "80 XP more to Level 4"
4. **Palabra del día** — Card with gradient icon square, large Spanish word, pronunciation, tap-to-reveal meaning, example sentence block (orange left border, warm bg)
5. **Frase del día** — RevealCard
6. **Frase corta** — RevealCard
7. **Palabras débiles** — List card: each item has red miss-count circle badge, Spanish word, tap to reveal English, miss count label
8. **Continue learning** — 4-column grid of action cards (icon + title + description) linking to Reader, Tarjetas, Frases, Viajes

**Data from Flask:** `homepage.word_of_day`, `homepage.daily_sentence`, `homepage.daily_phrase`, `homepage.weak_words`, `homepage.last_refresh_display`

**Gamification note:** The stats (XP, streak, level) need new data fields in the cache. Add to `cache.json`:
```json
{
  "user_stats": {
    "xp_total": 120,
    "xp_today": 40,
    "xp_daily_goal": 200,
    "level": 3,
    "streak_days": 7,
    "words_learned": 48,
    "accuracy_pct": 82
  }
}
```

### 2. Reader (`/reader` → `reader.html`)

**Layout:**
1. **Hero** — Pez (thinking), "Estudio Abroad Reader" label, "Read in Spanish. Hover to remember." title (primary color on "Hover to remember"), subtitle
2. **Instruction hint** — Orange-tinted bar with ◎ icon
3. **Passage cards** — Each card: header with language Badge (ES/CA) + title, then the fog-reveal interaction area
4. **Weak words section** — Same as home weak words but compact

**Fog-reveal:** Keep the existing `clip-path: circle()` mechanic but update the cursor ring to use `--teal` when active (border + box-shadow). The custom cursor is a 36px → 160px ring on hover.

**Key CSS for fog-reveal (already working, just restyle):**
```css
.passage-layer.translation {
  clip-path: circle(0px at var(--cx, 50%) var(--cy, 50%));
  transition: clip-path 0.08s ease;
  color: var(--teal);
  font-style: italic;
  background: var(--surface);
}
.passage-wrap.revealing .passage-layer.translation {
  clip-path: circle(80px at var(--cx, 50%) var(--cy, 50%));
}
```

### 3. Vocab / Flashcards (`/vocab` → `vocab.html`)

**States:** Active session → Session complete

**Active session layout:**
1. **Header** — "Tarjetas" h1 + subtitle
2. **Progress bar** — "Card N of M" + correct/missed count + gradient progress bar
3. **Flashcard** — Large card (520px max-width), centered Spanish word (36px/800), "👁 Tap to reveal" pill button. On reveal: English appears below with border-top divider
4. **Action buttons** — "✓ Correct" (green) + "✗ Missed" (danger) — appear after reveal
5. **Pez** — below card, changes expression based on state

**Session complete layout:**
1. Pez (celebrating or thinking based on score) with speech
2. "Session Complete" heading
3. Correct/Missed StatCards side by side
4. "+N XP" earned card
5. Missed words recap list (if any)
6. "Practice Again" button

**Celebration overlay:** On correct answer, show fullscreen overlay with Pez celebrating + "¡Correcto!" + "+10 XP" — auto-dismiss after 1.8s

**XP logic:** +10 XP per correct answer. Update `user_stats.xp_total` and `user_stats.xp_today` on each correct.

### 4. Phrasebook (`/phrasebook` → `phrasebook.html`)

**Layout:**
1. **Header** — "Libro de frases" h1 + "Export CSV" secondary button
2. **Add phrase card** — Input with "Translate & Save" primary button
3. **Reveal hint** — Orange bar
4. **Phrases list card** — Header shows count. Each row: Spanish text (click to reveal English), Edit + Delete buttons. Edit opens inline input below.

**Empty state:** Pez (thinking) + "No phrases yet" message

### 5. Travel (`/travel` → `travel.html`)

**Layout:** 2-column grid (280px sidebar + fluid content)
1. **Sidebar: Filters** — Card with select dropdowns (Time, Location, Distance, Mood) + Search button
2. **Main: Map** — Leaflet map placeholder (keep existing Leaflet integration, just restyle container: 300px height, `--radius-lg`, border)
3. **Main: Results** — Cards with name, address, RevealCard for description, Google Maps link

**Empty/no-search state:** Pez with speech bubble "Choose filters and search!"

### 6. News (`/news` → `news.html`)

**Layout:** Responsive card grid (min 340px columns)
- Each card: 4px gradient top bar (rotating colors), title (16px/700), source + date, description, "Leer más" button
- Footer: "News from NewsAPI · Cached for 60 minutes"

### 7. History (`/history` → `history.html`)

**Layout:**
1. **Tab bar** — Horizontal tabs with bottom border indicator (primary color)
2. **Content card** — Title, intro, Spanish summary, "Show in English" toggle button, English text (teal, italic, left border), Wikipedia link

### 8. Resources (`/resources` → `resources.html`)

**Layout:** Responsive card grid (min 300px columns)
- Each card: 4px colored top bar, name + skill Badge, RevealCard for description, "Visit site" link

---

## Dark Mode Implementation

Add a `dark` class to `<body>`. All components swap their token values:

```css
body.dark {
  --bg: var(--dark-bg);
  --surface: var(--dark-surface);
  --text: var(--dark-text);
  --text-secondary: var(--dark-text-secondary);
  --border: var(--dark-border);
  /* ... etc */
}
```

Store preference in `localStorage`:
```js
const savedTheme = localStorage.getItem('theme');
if (savedTheme === 'dark') document.body.classList.add('dark');

function toggleTheme() {
  document.body.classList.toggle('dark');
  localStorage.setItem('theme', document.body.classList.contains('dark') ? 'dark' : 'light');
}
```

---

## Footer

```html
<footer>
  <div class="footer-inner">
    <div class="footer-brand">
      <!-- Pez SVG (28px, wink) -->
      <span class="footer-name">Estudio Abroad</span>
    </div>
    <p class="footer-tagline">Estudio de español en Barcelona</p>
    {% if homepage and homepage.last_refresh_display %}
    <p class="footer-refresh">Last cache refresh: {{ homepage.last_refresh_display }}</p>
    {% endif %}
    <p class="footer-credit">
      Created by and for <a href="https://github.com/xandermckie">Xander McKie</a>
    </p>
  </div>
</footer>
```

---

## Migration Checklist

1. **Replace `base.html`** — New font imports, new CSS variables, new navbar markup, footer update
2. **Update each page template** — Apply new card/component classes, replace `.click-reveal` with `.reveal-card`
3. **Add Pez SVG partial** — `templates/partials/pez.html` macro
4. **Add gamification data** — New `user_stats` object in cache, XP/streak tracking in `fetcher.py`
5. **Add dark mode** — Body class toggle, CSS variable swaps, localStorage persistence
6. **Add celebration overlay** — JS component for flashcard correct answers
7. **Remove** — All Playfair Display / Source Serif 4 font references, old dark-theme CSS variables, Quick Links footer section
8. **Test** — All 8 routes render correctly, fog-reveal still works, flashcard recording still works, phrasebook CRUD still works

---

## File Reference

| Prototype File | What It Contains |
|---|---|
| `mascot.jsx` | Pez SVG component with 6 expressions — port to Jinja2 macro |
| `ui-components.jsx` | All design tokens + Navbar, Card, Badge, Btn, XPBar, StreakBadge, StatCard, RevealCard, Footer, CelebrationOverlay |
| `page-home.jsx` | Home page layout and all sections |
| `page-reader.jsx` | Reader page with fog-reveal interaction |
| `page-vocab.jsx` | Flashcard session + results screen |
| `page-phrasebook-travel.jsx` | Phrasebook CRUD + Travel filters/results |
| `page-news-history-resources.jsx` | News grid, History tabs, Resources grid |
| `Estudio Abroad.html` | Main entry point that assembles everything |

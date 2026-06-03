# Estudio Abroad — Design System

Inspired by Duolingo + Mango Languages. Clean, bright, approachable. This is a web app — optimize for desktop-first with responsive support, not mobile-only.

---

## Brand Identity

**App name:** Estudio Abroad  
**Mascot:** Pez — a blocky, cute red-and-yellow fish with a graduation cap  
**Personality:** Friendly, encouraging, colorful — like a study buddy, not a textbook

---

## Color Palette

| Token | Hex | Use |
|---|---|---|
| `--color-red` | `#C60B1E` | Primary brand, CTAs, mascot body, active nav |
| `--color-yellow` | `#FFC400` | Accent, mascot fins, badges, highlights |
| `--color-navy` | `#1A1A2E` | Text primary, mascot hat, dark accents |
| `--color-bg` | `#F8F7F2` | Page background (warm off-white, not pure white) |
| `--color-surface` | `#FFFFFF` | Cards, modals, inputs |
| `--color-text` | `#2D2D3A` | Body text |
| `--color-muted` | `#6B7280` | Secondary text, timestamps, labels |
| `--color-border` | `#E5E7EB` | Borders, dividers |
| `--color-green` | `#58CC02` | Correct answers, success states (Duolingo green) |
| `--color-red-light` | `#FFF0F0` | Error backgrounds |
| `--color-yellow-light` | `#FFFBEB` | Warning / hint backgrounds |

**Remove entirely:** the old dark theme (`--bg: #0e0d0b`, `--surface: #16140f`, etc.)

---

## Typography

**Replace Playfair Display + Source Serif 4 with:**

```css
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap');

:root {
  --font-display: 'Nunito', system-ui, sans-serif;   /* headings, nav brand, mascot name */
  --font-body:    'Inter', system-ui, sans-serif;     /* body text, inputs, labels */
}
```

| Role | Font | Weight | Size |
|---|---|---|---|
| App name / h1 | Nunito | 800 | 2rem |
| Section headings / h2 | Nunito | 700 | 1.5rem |
| Card headers / h3 | Nunito | 700 | 1.1rem |
| Body text | Inter | 400 | 1rem |
| Labels, metadata | Inter | 500 | 0.85rem |
| Muted / timestamps | Inter | 400 | 0.8rem |

---

## Components

### Cards
```css
.card {
  background: #FFFFFF;
  border: 1.5px solid #E5E7EB;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  padding: 1.5rem;
}
.card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  transform: translateY(-1px);
  transition: all 0.15s ease;
}
```

### Buttons
- **Primary:** `background: #C60B1E`, white text, `border-radius: 50px` (pill), `padding: 0.6rem 1.5rem`, `font-weight: 700`
- **Secondary:** white background, `border: 2px solid #C60B1E`, red text, same pill shape
- **Success:** `background: #58CC02`, white text
- No ghost buttons. All buttons have clear backgrounds.

### Navbar
- Background: `#FFFFFF`, bottom border `1.5px solid #E5E7EB`
- Show Pez mascot SVG (32px tall) left of the "Estudio Abroad" wordmark
- Active nav link: `color: #C60B1E`, `font-weight: 700`, small red underline indicator
- Inactive nav links: `color: #6B7280`
- Font: Nunito 600

### Click-to-Reveal (Spanish → English)
Replace the old dark hint bar with a bright pill:
```html
<div class="reveal-hint">
  👆 Toca para ver en inglés
</div>
```
```css
.reveal-hint {
  background: #FFFBEB;
  border: 1.5px solid #FFC400;
  border-radius: 50px;
  padding: 0.4rem 1rem;
  font-size: 0.85rem;
  color: #92600A;
  display: inline-block;
  margin-bottom: 1rem;
}
.click-reveal-en {
  color: #C60B1E;
  font-style: italic;
  font-weight: 600;
}
```

### Flash / Alert Messages
| Type | Background | Border | Text |
|---|---|---|---|
| Success | `#F0FDF4` | `#58CC02` | `#166534` |
| Warning | `#FFFBEB` | `#FFC400` | `#92600A` |
| Error | `#FFF0F0` | `#C60B1E` | `#991B1B` |
| Info | `#EFF6FF` | `#3B82F6` | `#1E40AF` |

Always border-left accent style (4px), `border-radius: 12px`, no harsh box.

### Section Headers
Each page section should have a small colored pill category tag above the heading:
```html
<span class="section-tag">📖 Vocabulario</span>
<h2>Palabra del día</h2>
```
```css
.section-tag {
  background: #FFF0F0;
  color: #C60B1E;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.2rem 0.75rem;
  border-radius: 50px;
  letter-spacing: 0.04em;
  display: inline-block;
  margin-bottom: 0.5rem;
}
```

### Weak Words List
Replace plain `<ol>` with ranked cards:
- Each word gets its own small card
- A colored miss-count badge: red pill showing "3 errores"
- Subtle left border in red

### Footer
White background, light top border. Pez mascot (24px) inline with app name.

---

## Layout

- **Max content width:** `960px` (container), centered
- **Page background:** `#F8F7F2`
- **Card grid:** Bootstrap `row-cols-1 row-cols-md-2 row-cols-lg-3 g-3`
- **Section spacing:** `py-5` between major sections
- **No full-bleed dark sections**

---

## Mascot — Pez

**SVG file:** Save as `static/img/pez.svg`  
**Design:** Blocky, geometric fish. Red body, yellow tail/dorsal fin, navy graduation cap, big expressive eye with highlight, cute smile, rosy cheek blush.

### Usage rules
| Size | Use |
|---|---|
| 40px tall | Navbar (next to brand name) |
| 64px tall | Homepage hero / section intro |
| 24px tall | Footer |
| 128px tall | Error/empty state illustrations |
| Favicon | Simplify to body + eye only, no cap |

### SVG source
Place the SVG from the design reference into `static/img/pez.svg`. Embed inline in navbar for best color control. Reference as `<img>` elsewhere.

**Key SVG elements:**
- Body: `<rect rx="28" fill="#C60B1E">`
- Tail lobes: `<polygon fill="#FFC400">` and `<polygon fill="#E8A800">` (two values for depth)
- Dorsal fin: `<polygon fill="#FFC400">`
- Eye: white circle + navy circle + blue iris + dark pupil + two white highlights
- Cheek: `<ellipse fill="#FF6B8A" opacity="0.35">`
- Scale dots: small dark red circles in a grid pattern on the body's right half
- Cap: two dark navy rects + yellow tassel line + yellow circle

---

## Bootstrap 5 Overrides

Add this CSS block in `base.html` `<style>` to override Bootstrap defaults:

```css
:root {
  --bs-primary: #C60B1E;
  --bs-primary-rgb: 198, 11, 30;
  --bs-body-bg: #F8F7F2;
  --bs-body-color: #2D2D3A;
  --bs-border-radius: 12px;
  --bs-border-radius-lg: 16px;
  --bs-border-radius-pill: 50rem;
  --bs-font-sans-serif: 'Inter', system-ui, sans-serif;
}
.btn-primary {
  background-color: #C60B1E;
  border-color: #C60B1E;
  border-radius: 50px;
  font-weight: 700;
  font-family: 'Nunito', sans-serif;
}
.btn-primary:hover { background-color: #A50818; border-color: #A50818; }
```
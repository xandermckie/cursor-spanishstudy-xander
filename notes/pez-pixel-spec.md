# Pez pixel-art spec (reference layout)

Grid: **7 rows × ~28 cols**, origin `(11, 26)`, **2×2** SVG units per cell, `viewBox="0 0 80 80"`.

## Layout (facing left)

| Segment | Cols (approx) | Color |
|---------|---------------|-------|
| Head | 7–11 | `#FFC400` yellow |
| Body | 12–19 | `#C60B1E` red |
| Tail | 20+ | `#FFC400` yellow (flared rows 1–3) |

Side fin: yellow patch + navy diagonal on body row 4. Tail rays: navy pixels rows 1–3 at body–tail join.

## Palette

| Code | Role | Hex |
|------|------|-----|
| Y | Head, tail, side fin | `#FFC400` |
| R | Body | `#C60B1E` |
| N | Eye, mouth, fin line, tail rays | `#1A1A2E` |
| W | Eye highlight (one pixel) | `#F8F1F2` |
| B | Blush (expressions) | `#FF6B8A` |

## Happy base (body only — no face)

```
.......YYYYYRRRRRRRRYYYYY.........
......YYYYYYYRRRRRRRRNYYYYYYY......
......YYYYYYYRRRRRRRRYNYYYYYYY.....
......YYYYYYYRRRRRRRRYYNYYYYYY.....
......YYYYYYRRRYNRRYYYYYYYYY......
......YYYYYYYRRRRRRRRYYYYYYY......
.......YYYYYRRRRRRRRYYYYY.........
```

Face overlays use `col_offset=7` on head.

## Expression deltas

| Expression | Eye (head) | Mouth | Blush |
|------------|------------|-------|-------|
| **happy** | 3×3 `N` + `W` highlight top-left of pupil | 2-step `N` under eye | 2× `B` on cheek |
| **wink** | Navy bar rows 2–3 cols 7–10 | Same as happy | Yes |
| **sleeping** | Single `N` row | One `N` | Yes |
| **celebrating** | 4×4 `N` + `W` highlight | +1 mouth pixel | Yes |
| **thinking** | 2×2 `N` | Flat `NNN` bar | No |
| **excited** | Same as happy | Wide mouth | Yes |

## Regenerate

```bash
python scripts/gen_pez_rects.py body > templates/partials/pez_body_pixels.html
python scripts/gen_pez_rects.py eye_happy > templates/partials/pez_eye_happy_pixels.html
# ... other layers per scripts/gen_pez_rects.py main()
```

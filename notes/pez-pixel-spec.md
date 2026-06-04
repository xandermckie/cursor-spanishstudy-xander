# Pez pixel-art spec

Grid: **28×16** logical cells, origin `(12, 18)`, **2×2** SVG units per cell, `viewBox="0 0 80 80"`.

## Palette

| Code | Role | Hex |
|------|------|-----|
| R | Body | `#C60B1E` |
| A | Belly / gills | `#A30B18` |
| Y | Fins | `#FFC400` |
| E | Fin depth | `#E8A800` |
| W | Eye white | `#F8F1F2` |
| N | Pupil / mouth | `#1A1A2E` |
| B | Blush | `#FF6B8A` |

## Happy base (body + fins, no face)

```
..............YY..............
............YYYY..............
...........RRRR...............
.........RRRRRRRR.............
...........RRRRRRRRRRRR.......
..........RRRRRRRRRRRRRR..YY..
.........RRRRRRRRRRRRRR.YYYY.
........RRRRRRRRRRRRRRRYYYYY.
........RRRRRRRRRRRRRRR.YYYY.
.........RRRRRAAARRRRRR.YYY..
.........RRRRAAAAARRRRR.YY...
..........RRRRRAAARRRRR.......
...........RRRRRRRRRR.........
```

Profile faces **left** (eye col 2–6, tail col 20+). No cap.

## Expression deltas

| Expression | Eye | Mouth | Blush |
|------------|-----|-------|-------|
| **happy** | 6×6 white + 2×2 pupil + white highlight at `(20,34)` (grid `W`, not duplicate rect) | Stepped NN at rows 14–15 | Yes `(18,44)` |
| **wink** | Navy bar rows 4–5 cols 4–7 | Same as happy | Yes |
| **sleeping** | Single navy bar row 5 | One pixel row 15 | Yes |
| **celebrating** | Taller/wider eye (extra W rows) | +1 mouth pixel | Yes |
| **thinking** | Smaller 4×4 eye | Flat NNNN bar row 15 | No |
| **excited** | Same as happy | Wider mouth (+1 step) | Yes |

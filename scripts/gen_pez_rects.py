"""Emit Pez pixel <rect> layers from ASCII grids."""
from __future__ import annotations
import sys

OX, OY, P = 12, 18, 2
COLORS = {
    "R": "#C60B1E",
    "A": "#A30B18",
    "Y": "#FFC400",
    "E": "#E8A800",
    "W": "#F8F1F2",
    "N": "#1A1A2E",
    "B": "#FF6B8A",
}

BODY = """
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
"""

EYE_HAPPY = """
...WWW.....
..WWWW....
.WWNNWW...
.WNNNNW...
.WWNWW....
..WWWW....
"""

EYE_WIDE = """
..WWWW....
.WWWWWW...
.WWNNWW...
.WNNNNW...
.WWNNWW...
..WWWW....
"""

EYE_SMALL = """
...WW......
..WNNW......
..WNNW......
...WW.......
"""

EYE_WINK = """
....NNNN....
....NNNN....
"""

EYE_SLEEP = """
.....NN.....
"""

MOUTH_HAPPY = """
..NN.......
...NN......
"""

MOUTH_WIDE = """
..NN.......
...NN......
....NN.....
"""

MOUTH_FLAT = """
...NNNN....
"""

MOUTH_TINY = """
...N.......
"""

BLUSH = """
...B.......
"""


def emit(grid: str, row_offset: int = 0) -> list[str]:
    out: list[str] = []
    for r, row in enumerate(grid.strip().splitlines()):
        for c, ch in enumerate(row):
            if ch in COLORS:
                x, y = OX + c * P, OY + (r + row_offset) * P
                out.append(
                    f'    <rect x="{x}" y="{y}" width="{P}" height="{P}" fill="{COLORS[ch]}"/>'
                )
    return out


def main() -> None:
    layer = sys.argv[1] if len(sys.argv) > 1 else "body"
    if layer == "body":
        rects = emit(BODY)
        for c, r in [(26, 8), (27, 9), (27, 10)]:
            x, y = OX + c * P, OY + r * P
            rects.append(
                f'    <rect x="{x}" y="{y}" width="{P}" height="{P}" fill="{COLORS["E"]}"/>'
            )
    elif layer == "eye_happy":
        rects = emit(EYE_HAPPY, row_offset=4)
    elif layer == "eye_wide":
        rects = emit(EYE_WIDE, row_offset=3)
        # Extra sparkle beside wide eye (not in ASCII row width)
        rects.append(
            f'    <rect x="{OX + 6 * P}" y="{OY + 8 * P}" width="{P}" height="{P}" fill="{COLORS["W"]}"/>'
        )
    elif layer == "eye_small":
        rects = emit(EYE_SMALL, row_offset=5)
    elif layer == "eye_wink":
        rects = emit(EYE_WINK, row_offset=4)
    elif layer == "eye_sleep":
        rects = emit(EYE_SLEEP, row_offset=5)
    elif layer == "mouth_happy":
        rects = emit(MOUTH_HAPPY, row_offset=14)
    elif layer == "mouth_wide":
        rects = emit(MOUTH_WIDE, row_offset=14)
    elif layer == "mouth_flat":
        rects = emit(MOUTH_FLAT, row_offset=15)
    elif layer == "mouth_tiny":
        rects = emit(MOUTH_TINY, row_offset=15)
    elif layer == "blush":
        rects = emit(BLUSH, row_offset=13)
    else:
        raise SystemExit(f"unknown layer {layer}")
    print("\n".join(rects))


if __name__ == "__main__":
    main()

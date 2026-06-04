"""Emit Pez pixel <rect> layers from ASCII grids (reference: yellow head, red body, yellow tail)."""
from __future__ import annotations
import sys

OX, OY, P = 11, 26, 2
COLORS = {
    "R": "#C60B1E",
    "Y": "#FFC400",
    "W": "#F8F1F2",
    "N": "#1A1A2E",
    "B": "#FF6B8A",
}

# Base fish: no eye/mouth (overlays on yellow head cols 7-11)
BODY = """
.......YYYYYRRRRRRRRYYYYY.........
......YYYYYYYRRRRRRRRNYYYYYYY......
......YYYYYYYRRRRRRRRYNYYYYYYY.....
......YYYYYYYRRRRRRRRYYNYYYYYY.....
......YYYYYYRRRYNRRYYYYYYYYY......
......YYYYYYYRRRRRRRRYYYYYYY......
.......YYYYYRRRRRRRRYYYYY.........
"""

EYE_HAPPY = """
..NNN
.NNW.
.NN..
"""

EYE_WIDE = """
.NNNN
NNNNN
NNWNN
.NNN.
"""

EYE_SMALL = """
.NN
NN.
"""

EYE_WINK = """
.NNNN
.NNNN
"""

EYE_SLEEP = """
..N..
"""

MOUTH_HAPPY = """
..N.
...N
"""

MOUTH_WIDE = """
..N.
...N
....N
"""

MOUTH_FLAT = """
..NNN
"""

MOUTH_TINY = """
..N..
"""

BLUSH = """
.B.
.B.
"""


def emit(grid: str, row_offset: int = 0, col_offset: int = 0) -> list[str]:
    out: list[str] = []
    for r, row in enumerate(grid.strip().splitlines()):
        for c, ch in enumerate(row):
            if ch in COLORS:
                x = OX + (c + col_offset) * P
                y = OY + (r + row_offset) * P
                out.append(
                    f'    <rect x="{x}" y="{y}" width="{P}" height="{P}" fill="{COLORS[ch]}"/>'
                )
    return out


def main() -> None:
    layer = sys.argv[1] if len(sys.argv) > 1 else "body"
    head_col = 7
    if layer == "body":
        rects = emit(BODY)
    elif layer == "eye_happy":
        rects = emit(EYE_HAPPY, row_offset=2, col_offset=head_col)
    elif layer == "eye_wide":
        rects = emit(EYE_WIDE, row_offset=1, col_offset=head_col)
    elif layer == "eye_small":
        rects = emit(EYE_SMALL, row_offset=3, col_offset=head_col + 1)
    elif layer == "eye_wink":
        rects = emit(EYE_WINK, row_offset=2, col_offset=head_col)
    elif layer == "eye_sleep":
        rects = emit(EYE_SLEEP, row_offset=3, col_offset=head_col + 1)
    elif layer == "mouth_happy":
        rects = emit(MOUTH_HAPPY, row_offset=4, col_offset=head_col)
    elif layer == "mouth_wide":
        rects = emit(MOUTH_WIDE, row_offset=4, col_offset=head_col)
    elif layer == "mouth_flat":
        rects = emit(MOUTH_FLAT, row_offset=5, col_offset=head_col)
    elif layer == "mouth_tiny":
        rects = emit(MOUTH_TINY, row_offset=5, col_offset=head_col + 1)
    elif layer == "blush":
        rects = emit(BLUSH, row_offset=5, col_offset=head_col - 1)
    else:
        raise SystemExit(f"unknown layer {layer}")
    print("\n".join(rects))


if __name__ == "__main__":
    main()

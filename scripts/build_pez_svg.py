"""Assemble static/img/pez.svg from happy pixel partials."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTIALS = ROOT / "templates" / "partials"
PARTS = ("body", "eye_happy", "mouth_happy", "blush")


def main() -> None:
    inner = "\n".join(
        (PARTIALS / f"pez_{name}_pixels.html").read_text(encoding="utf-8").strip()
        for name in PARTS
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" '
        'shape-rendering="crispEdges" aria-label="Pez mascot">\n'
        f"{inner}\n"
        "</svg>\n"
    )
    (ROOT / "static" / "img" / "pez.svg").write_text(svg, encoding="utf-8")
    print("wrote pez.svg")


if __name__ == "__main__":
    main()

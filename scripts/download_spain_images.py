"""Download or generate Spain gallery images for static/img/spain/."""

from __future__ import annotations

import struct
import zlib
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "EstudioAbroad/1.0 (educational; local seed script)"

IMAGES: dict[str, str] = {
    "barcelona-skyline.png": (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/"
        "Barcelona_-_panorama_de_la_ciutat_des_de_Montju%C3%AFc.jpg/"
        "330px-Barcelona_-_panorama_de_la_ciutat_des_de_Montju%C3%AFc.jpg"
    ),
    "sagrada-familia.png": (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/"
        "Sagrada_Familia_01.jpg/330px-Sagrada_Familia_01.jpg"
    ),
    "spanish-tapas.png": (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/"
        "La_Boqueria.JPG/330px-La_Boqueria.JPG"
    ),
    "park-guell.png": (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4f/"
        "Parc_guell_1.jpg/330px-Parc_guell_1.jpg"
    ),
    "barcelona-beach.png": (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/"
        "Barceloneta_Beach.jpg/330px-Barceloneta_Beach.jpg"
    ),
    "placa-catalunya.png": (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/"
        "Pla%C3%A7a_de_Catalunya.jpg/330px-Pla%C3%A7a_de_Catalunya.jpg"
    ),
}

FALLBACK_COLORS: dict[str, tuple[int, int, int]] = {
    "barcelona-skyline.png": (200, 90, 60),
    "sagrada-familia.png": (180, 160, 140),
    "spanish-tapas.png": (180, 110, 70),
    "park-guell.png": (60, 160, 120),
    "barcelona-beach.png": (70, 150, 200),
    "placa-catalunya.png": (90, 100, 160),
}

OUT_DIR = Path(__file__).resolve().parent.parent / "static" / "img" / "spain"
WIDTH, HEIGHT = 640, 400


def _write_flat_png(path: Path, rgb: tuple[int, int, int]) -> None:
    r, g, b = rgb

    def _chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    raw = b""
    row = bytes([r, g, b] * WIDTH)
    for _ in range(HEIGHT):
        raw += b"\x00" + row
    compressed = zlib.compress(raw, 9)
    ihdr = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", compressed)
        + _chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, url in IMAGES.items():
        dest = OUT_DIR / filename
        print(f"Fetching {filename}...")
        try:
            data = _fetch(url)
            dest.write_bytes(data)
            print(f"  -> {dest} ({dest.stat().st_size} bytes)")
        except (urllib.error.URLError, OSError) as exc:
            print(f"  download failed ({exc}); writing PNG fallback")
            color = FALLBACK_COLORS.get(filename, (100, 120, 150))
            _write_flat_png(dest, color)
            print(f"  -> {dest}")


if __name__ == "__main__":
    main()

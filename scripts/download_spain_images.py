"""Download or generate Spain gallery images for static/img/spain/."""

from __future__ import annotations

import struct
import zlib
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "EstudioAbroad/1.0 (educational; local seed script)"

# Gallery images are committed under static/img/spain/ (not downloaded here).
IMAGES: dict[str, str] = {}

FALLBACK_COLORS: dict[str, tuple[int, int, int]] = {
    "toledo-panorama.png": (180, 140, 90),
    "seville-flamenco.png": (200, 90, 60),
    "alicante-castle.png": (70, 150, 200),
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

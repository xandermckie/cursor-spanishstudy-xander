"""Homepage cache bootstrap tests."""

from __future__ import annotations

import json

import fetcher


def test_bootstrap_homepage_cache_fills_daily_content(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    cache_file = data_dir / "cache.json"
    cache_file.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(fetcher, "DATA_DIR", data_dir)
    monkeypatch.setattr(fetcher, "CACHE_FILE", cache_file)

    assert fetcher._bootstrap_homepage_cache() is True

    cache = json.loads(cache_file.read_text(encoding="utf-8"))
    assert cache["daily_sentence"]["es"]
    assert cache["daily_sentence"]["en"]
    assert cache["daily_phrase"]["es"]
    assert cache["daily_phrase"]["en"]
    assert cache["word_of_day"]["es"]
    assert cache.get("flashcard_deck")


def test_get_homepage_bootstraps_empty_cache(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    cache_file = data_dir / "cache.json"
    cache_file.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(fetcher, "DATA_DIR", data_dir)
    monkeypatch.setattr(fetcher, "CACHE_FILE", cache_file)
    monkeypatch.setattr(
        fetcher,
        "refresh_homepage",
        lambda: fetcher._homepage_fallback(),
    )

    homepage = fetcher.get_homepage()
    assert homepage["daily_sentence"]
    assert homepage["daily_sentence"]["en"]
    assert homepage["error"] is False

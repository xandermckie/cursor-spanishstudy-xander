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
    assert cache["daily_sentence"]["en"] != cache["daily_sentence"]["es"]
    assert cache["daily_phrase"]["es"]
    assert cache["daily_phrase"]["en"]
    assert cache["daily_phrase"]["en"] != cache["daily_phrase"]["es"]
    assert cache["word_of_day"]["es"]
    wod = cache["word_of_day"]
    assert wod["en"]
    assert wod["en"] != wod["es"]
    assert wod.get("definition") or wod.get("definition_es")
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
    assert homepage["daily_sentence"]["en"] != homepage["daily_sentence"]["es"]
    assert homepage["error"] is False


def test_repair_invalid_spanish_as_english_cache(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    cache_file = data_dir / "cache.json"
    bad = {
        "daily_sentence": {"es": "Hola mundo.", "en": "Hola mundo."},
        "daily_phrase": {"es": "gracias", "en": "gracias"},
        "word_of_day": {"es": "estación", "en": "estación", "definition": ""},
    }
    cache_file.write_text(json.dumps(bad), encoding="utf-8")

    monkeypatch.setattr(fetcher, "DATA_DIR", data_dir)
    monkeypatch.setattr(fetcher, "CACHE_FILE", cache_file)

    homepage = fetcher.get_homepage()
    assert homepage["daily_sentence"]["en"] != homepage["daily_sentence"]["es"]
    assert homepage["word_of_day"]["en"] != homepage["word_of_day"]["es"]


def test_homepage_from_cache_valid_data_sets_error_false() -> None:
    cache = {
        "daily_sentence": {"es": "Buenos días.", "en": "Good morning."},
        "daily_phrase": {"es": "gracias", "en": "thank you"},
        "word_of_day": {"es": "estación", "en": "station"},
        "last_refresh": "2026-06-01T10:00:00+00:00",
    }
    result = fetcher._homepage_from_cache(cache)
    assert result is not None
    assert result["daily_sentence"]["en"] == "Good morning."
    assert result["daily_phrase"]["en"] == "thank you"
    assert result["error"] is False


def test_homepage_from_cache_invalid_returns_none() -> None:
    assert fetcher._homepage_from_cache({}) is None
    assert (
        fetcher._homepage_from_cache(
            {
                "daily_sentence": {"es": "Hola.", "en": "Hello."},
                "daily_phrase": {"es": "gracias"},
            }
        )
        is None
    )


def test_get_home_gallery_returns_rotated_items() -> None:
    items = fetcher.get_home_gallery(3)
    assert len(items) == 3
    assert all(item.get("url", "").startswith("img/spain/") for item in items)
    assert all(item.get("caption_es") for item in items)

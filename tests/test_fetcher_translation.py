"""Tests for parallel translation fallbacks and homepage cache skipping."""

from __future__ import annotations

import time
from datetime import datetime, timezone

import fetcher


def test_fetch_translation_uses_first_parallel_success(monkeypatch) -> None:
    calls: list[str] = []

    def slow_mymemory(*_args, **_kwargs) -> None:
        calls.append("mymemory")
        return None

    def fast_lingva(*_args, **_kwargs) -> str:
        calls.append("lingva")
        return "hola"

    monkeypatch.setattr(fetcher.translation, "_fetch_mymemory", slow_mymemory)
    monkeypatch.setattr(fetcher.translation, "_fetch_lingva_instance", fast_lingva)
    monkeypatch.setattr(fetcher.translation, "_fetch_libretranslate", lambda *_a, **_k: None)
    monkeypatch.setattr(fetcher.translation, "LINGVA_URLS", ("https://lingva.example/api/v1",))

    translated, from_cache = fetcher.fetch_translation("hello", "en", "es", use_cache=False)

    assert translated == "hola"
    assert from_cache is False
    assert "lingva" in calls


def test_fetch_translation_live_short_circuits_on_first_success(
    monkeypatch,
) -> None:
    def fast_lingva(*_args, **_kwargs) -> str:
        time.sleep(0.05)
        return "hola"

    def slow_mymemory(*_args, **_kwargs) -> None:
        time.sleep(2.0)
        return None

    monkeypatch.setattr(fetcher.translation, "_fetch_lingva_instance", fast_lingva)
    monkeypatch.setattr(fetcher.translation, "_fetch_mymemory", slow_mymemory)
    monkeypatch.setattr(fetcher.translation, "_fetch_libretranslate", lambda *_a, **_k: None)
    monkeypatch.setattr(fetcher.translation, "LINGVA_URLS", ("https://lingva.example/api/v1",))

    started = time.monotonic()
    translated = fetcher.translation._fetch_translation_live("hello", "en", "es", timeout=8)
    elapsed = time.monotonic() - started

    assert translated == "hola"
    assert elapsed < 0.5


def test_homepage_cache_fresh_skips_api_calls(monkeypatch, tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    cache_file = data_dir / "cache.json"
    today = datetime.now(timezone.utc).date().isoformat()
    sentence_es = fetcher.DAILY_SENTENCES_ES[fetcher._utc_day_index(len(fetcher.DAILY_SENTENCES_ES))]
    phrase_es = fetcher.DAILY_PHRASES_ES[
        (fetcher._utc_day_index(len(fetcher.DAILY_SENTENCES_ES)) + 11)
        % len(fetcher.DAILY_PHRASES_ES)
    ]
    cache_file.write_text(
        (
            '{"daily_sentence":{"es":"'
            + sentence_es.replace('"', '\\"')
            + '","en":"English sentence","fetched_at":"'
            + today
            + 'T12:00:00+00:00"},"daily_phrase":{"es":"'
            + phrase_es.replace('"', '\\"')
            + '","en":"English phrase","fetched_at":"'
            + today
            + 'T12:00:00+00:00"}}'
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("fetcher.cache.DATA_DIR", data_dir)
    monkeypatch.setattr("fetcher.cache.CACHE_FILE", cache_file)
    monkeypatch.setattr(fetcher, "DATA_DIR", data_dir)
    monkeypatch.setattr(fetcher, "CACHE_FILE", cache_file)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("fetch_translation should not run when cache is fresh")

    monkeypatch.setattr(fetcher, "fetch_translation", fail_if_called)

    cache = fetcher._load_cache()
    assert fetcher._populate_homepage_cache(cache, use_apis=True) is True


def test_store_translation_evicts_oldest_when_over_limit(tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    cache_file = data_dir / "cache.json"
    cache_file.write_text("{}", encoding="utf-8")

    import fetcher as fetcher_mod

    import fetcher.cache as cache_mod

    original_data_dir = cache_mod.DATA_DIR
    original_cache_file = cache_mod.CACHE_FILE
    cache_mod.DATA_DIR = data_dir
    cache_mod.CACHE_FILE = cache_file
    fetcher_mod.DATA_DIR = data_dir
    fetcher_mod.CACHE_FILE = cache_file
    try:
        cache = fetcher_mod._load_cache()
        for i in range(fetcher_mod.MAX_TRANSLATION_CACHE + 1):
            fetcher_mod._store_translation(cache, f"key-{i}", f"value-{i}")

        translations = cache["translations"]
        assert len(translations) == fetcher_mod.MAX_TRANSLATION_CACHE
        assert "key-0" not in translations
        assert f"key-{fetcher_mod.MAX_TRANSLATION_CACHE}" in translations
    finally:
        cache_mod.DATA_DIR = original_data_dir
        cache_mod.CACHE_FILE = original_cache_file
        fetcher_mod.DATA_DIR = original_data_dir
        fetcher_mod.CACHE_FILE = original_cache_file


def test_fetch_translation_fast_uses_shorter_timeout(monkeypatch) -> None:
    captured: list[int] = []

    def capture_timeout(*_args, timeout: int = 12, **_kwargs) -> str:
        captured.append(timeout)
        return "hola"

    monkeypatch.setattr(fetcher.translation, "_fetch_translation_live", capture_timeout)
    monkeypatch.setattr(fetcher.translation, "_load_cache", lambda: {"translations": {}})

    fetcher.fetch_translation_fast("hello", "en", "es", use_cache=False)

    assert captured == [8]


def test_wikipedia_refresh_handles_naive_timestamp(monkeypatch, tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    cache_file = data_dir / "cache.json"
    cache_file.write_text(
        '{"wikipedia_passages":[],"wikipedia_last_fetch":"2026-01-01T00:00:00"}',
        encoding="utf-8",
    )
    monkeypatch.setattr("fetcher.cache.DATA_DIR", data_dir)
    monkeypatch.setattr("fetcher.cache.CACHE_FILE", cache_file)
    monkeypatch.setattr(fetcher, "DATA_DIR", data_dir)
    monkeypatch.setattr(fetcher, "CACHE_FILE", cache_file)
    monkeypatch.setattr(fetcher.core, "_fetch_wikipedia_article", lambda *_a, **_k: None)

    cache = fetcher._load_cache()
    fetcher._ensure_wikipedia_passages(cache)


def test_get_reader_excludes_pending_passages(monkeypatch, tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    cache_file = data_dir / "cache.json"
    cache_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("fetcher.cache.DATA_DIR", data_dir)
    monkeypatch.setattr("fetcher.cache.CACHE_FILE", cache_file)
    monkeypatch.setattr(fetcher, "DATA_DIR", data_dir)
    monkeypatch.setattr(fetcher, "CACHE_FILE", cache_file)
    monkeypatch.setattr(
        fetcher.core,
        "_ensure_reader_passages",
        lambda _cache: [
            {
                "id": "pending",
                "lang": "es",
                "title": "T",
                "body": "Hola",
                "_translation_pending": True,
            }
        ],
    )
    monkeypatch.setattr(fetcher.core, "_ensure_wikipedia_passages", lambda _cache: None)
    monkeypatch.setattr(fetcher.core, "get_weak_words", lambda *_a, **_k: [])
    monkeypatch.setattr(fetcher.core, "award_reader_xp", lambda *_a, **_k: None)

    result = fetcher.get_reader(None)

    assert result["section_failed"] is True
    assert result["passages"] == []

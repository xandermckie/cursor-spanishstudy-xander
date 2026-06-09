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

    monkeypatch.setattr(fetcher, "_fetch_mymemory", slow_mymemory)
    monkeypatch.setattr(fetcher, "_fetch_lingva_instance", fast_lingva)
    monkeypatch.setattr(fetcher, "_fetch_libretranslate", lambda *_a, **_k: None)
    monkeypatch.setattr(fetcher, "LINGVA_URLS", ("https://lingva.example/api/v1",))

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

    monkeypatch.setattr(fetcher, "_fetch_lingva_instance", fast_lingva)
    monkeypatch.setattr(fetcher, "_fetch_mymemory", slow_mymemory)
    monkeypatch.setattr(fetcher, "_fetch_libretranslate", lambda *_a, **_k: None)
    monkeypatch.setattr(fetcher, "LINGVA_URLS", ("https://lingva.example/api/v1",))

    started = time.monotonic()
    translated = fetcher._fetch_translation_live("hello", "en", "es", timeout=8)
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

    monkeypatch.setattr(fetcher, "DATA_DIR", data_dir)
    monkeypatch.setattr(fetcher, "CACHE_FILE", cache_file)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("fetch_translation should not run when cache is fresh")

    monkeypatch.setattr(fetcher, "fetch_translation", fail_if_called)

    cache = fetcher._load_cache()
    assert fetcher._populate_homepage_cache(cache, use_apis=True) is True

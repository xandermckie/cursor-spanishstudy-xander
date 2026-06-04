"""Regression tests for display-ready user stats."""
from __future__ import annotations

import fetcher


def test_get_user_stats_anonymous_includes_xp_bar_fields() -> None:
    stats = fetcher.get_user_stats(None)
    assert stats["xp_to_next_level"] == 100
    assert stats["xp_in_level"] == 0
    assert stats["xp_level_max"] == 100


def test_get_user_stats_fallback_when_user_load_fails(monkeypatch) -> None:
    def fail_load(_user_id: str) -> dict:
        raise OSError("user cache unavailable")

    monkeypatch.setattr(fetcher, "_load_user_cache", fail_load)
    stats = fetcher.get_user_stats("any-user-id")
    assert stats["xp_to_next_level"] == 100
    assert stats["xp_in_level"] == 0


def test_get_user_stats_max_level_has_zero_xp_to_next() -> None:
    cache = {
        "user_stats": {
            **fetcher._default_user_stats(),
            "xp_total": 1500,
            "level": 5,
        }
    }
    stats = fetcher._compute_user_stats(cache, global_cache={"flashcard_deck": []})
    assert stats["xp_to_next_level"] == 0
    assert stats["level"] == 5

"""Tests for time-of-day greetings."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import greetings

MADRID = ZoneInfo("Europe/Madrid")


def _madrid(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 6, 5, hour, minute, tzinfo=MADRID)


def test_morning_greeting() -> None:
    result = greetings.get_time_greeting(_madrid(6))
    assert result["title"] == "Buenos días"
    assert result["speech"] == "¡Hola! ¿Listo para aprender?"
    assert result["period"] == "morning"

    assert greetings.get_time_greeting(_madrid(12, 59))["period"] == "morning"


def test_afternoon_greeting() -> None:
    result = greetings.get_time_greeting(_madrid(13))
    assert result["title"] == "Buenas tardes"
    assert result["speech"] == "¡Hola! ¿Seguimos practicando?"
    assert result["period"] == "afternoon"

    assert greetings.get_time_greeting(_madrid(20, 59))["period"] == "afternoon"


def test_evening_greeting() -> None:
    result = greetings.get_time_greeting(_madrid(21))
    assert result["title"] == "Buenas noches"
    assert result["speech"] == "¡Hola! ¿Un repaso antes de dormir?"
    assert result["period"] == "evening"

    assert greetings.get_time_greeting(_madrid(5, 59))["period"] == "evening"


def test_naive_datetime_treated_as_madrid() -> None:
    naive = datetime(2026, 6, 5, 10, 0)
    result = greetings.get_time_greeting(naive)
    assert result["period"] == "morning"

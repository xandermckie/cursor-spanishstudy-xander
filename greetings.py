"""Time-of-day greetings for the home page (Europe/Madrid)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, TypedDict
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")
GreetingPeriod = Literal["morning", "afternoon", "evening"]


class TimeGreeting(TypedDict):
    title: str
    speech: str
    period: GreetingPeriod


_GREETINGS: dict[GreetingPeriod, TimeGreeting] = {
    "morning": {
        "title": "Buenos días",
        "speech": "¡Hola! ¿Listo para aprender?",
        "period": "morning",
    },
    "afternoon": {
        "title": "Buenas tardes",
        "speech": "¡Hola! ¿Seguimos practicando?",
        "period": "afternoon",
    },
    "evening": {
        "title": "Buenas noches",
        "speech": "¡Hola! ¿Un repaso antes de dormir?",
        "period": "evening",
    },
}


def _period_for_hour(hour: int) -> GreetingPeriod:
    if 6 <= hour < 13:
        return "morning"
    if 13 <= hour < 21:
        return "afternoon"
    return "evening"


def get_time_greeting(now: datetime | None = None) -> TimeGreeting:
    """Return greeting copy for the current hour in Europe/Madrid."""
    if now is None:
        now = datetime.now(MADRID)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=MADRID)
    else:
        now = now.astimezone(MADRID)

    return dict(_GREETINGS[_period_for_hour(now.hour)])

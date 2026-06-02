"""Orchestrate manual and scheduled data refresh from APIs."""

from __future__ import annotations

import logging
import random

from helpers import dictionary, glosbe, lingua, storage, translate

logger = logging.getLogger(__name__)


def run_full_refresh() -> dict:
    """
    Refresh daily sentence, warm caches, sample Glosbe, dictionary, and Lingua Robot.
    Returns {ok: bool, errors: list[str]}.
    """
    errors: list[str] = []

    try:
        translate.refresh_daily_sentence()
    except Exception as exc:
        logger.exception("Daily sentence refresh failed: %s", exc)
        errors.append("Daily sentence refresh failed.")

    translate.warm_cache_from_vocab()
    vocab = storage.get_vocab()

    if vocab:
        sample = random.sample(vocab, min(3, len(vocab)))
        for i, item in enumerate(sample):
            phrase = item.get("es", "")
            if phrase:
                examples = glosbe.fetch_examples_with_delay(
                    phrase, from_lang="es", to_lang="en", delay=0.5 if i > 0 else 0
                )
                if not examples:
                    errors.append(f"No examples for: {phrase[:40]}...")

    english_words = []
    for item in vocab:
        en = item.get("en", "")
        if en:
            first_word = en.split()[0].strip(".,?!").lower()
            if first_word and first_word not in english_words:
                english_words.append(first_word)

    if english_words:
        sample_words = random.sample(english_words, min(3, len(english_words)))
        for word in sample_words:
            details = dictionary.fetch_word_details(word, use_cache=False)
            if not details:
                errors.append(f"No definition found for: {word}")

    if vocab and lingua:
        spanish_words = []
        for item in vocab:
            es = item.get("es", "")
            if es:
                candidate = es.split()[0].strip("¿?,.'\"")
                if candidate and candidate not in spanish_words:
                    spanish_words.append(candidate)
        if spanish_words:
            for word in random.sample(spanish_words, min(2, len(spanish_words))):
                result = lingua.fetch_conjugation(word, lang="es", use_cache=False)
                if not result:
                    logger.debug("No Lingua Robot data for %r", word)

    ok = len(errors) == 0
    if ok:
        logger.info("Full refresh completed successfully.")
    else:
        logger.warning("Refresh completed with warnings: %s", errors)

    return {"ok": ok, "errors": errors}

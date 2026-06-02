"""Open Trivia DB and vocab quiz builders."""

from __future__ import annotations

import html
import logging
import random

import requests

from helpers import storage

logger = logging.getLogger(__name__)

TRIVIA_URL = "https://opentdb.com/api.php"


def fetch_trivia(count: int = 5) -> list[dict]:
    """Fetch multiple-choice trivia questions from Open Trivia DB."""
    try:
        params = {"amount": count, "type": "multiple"}
        response = requests.get(TRIVIA_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("response_code") != 0:
            logger.warning("Open Trivia DB response_code=%s", data.get("response_code"))
            return []
        results = data.get("results", [])
        questions = []
        for item in results:
            questions.append(
                {
                    "type": "trivia",
                    "question": html.unescape(item.get("question", "")),
                    "category": html.unescape(item.get("category", "")),
                    "difficulty": item.get("difficulty", ""),
                    "answers": randomize_answers(item),
                }
            )
        return questions
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.exception("Open Trivia DB failed: %s", exc)
        return []


def randomize_answers(question_dict: dict) -> list[dict[str, object]]:
    """Shuffle correct and incorrect answers."""
    correct = html.unescape(question_dict.get("correct_answer", ""))
    incorrect = [
        html.unescape(a) for a in question_dict.get("incorrect_answers", [])
    ]
    options = [{"text": correct, "correct": True}]
    for text in incorrect:
        options.append({"text": text, "correct": False})
    random.shuffle(options)
    return options


def build_vocab_questions(vocab: list[dict], n: int = 5) -> list[dict]:
    """Build ES-to-EN multiple choice from vocab entries."""
    if not vocab:
        return []

    pool = list(vocab)
    random.shuffle(pool)
    questions = []

    for item in pool[:n]:
        correct_en = item.get("en", "")
        es_prompt = item.get("es", "")
        if not correct_en or not es_prompt:
            continue

        category = item.get("category", "")
        wrong_pool = [
            v.get("en", "")
            for v in vocab
            if v.get("id") != item.get("id")
            and v.get("en")
            and v.get("category") == category
        ]
        if len(wrong_pool) < 3:
            wrong_pool = [
                v.get("en", "")
                for v in vocab
                if v.get("id") != item.get("id") and v.get("en")
            ]
        random.shuffle(wrong_pool)
        wrong = wrong_pool[:3]
        while len(wrong) < 3 and wrong_pool:
            wrong.append(random.choice(wrong_pool))

        options = [{"text": correct_en, "correct": True}]
        for text in wrong[:3]:
            if text != correct_en:
                options.append({"text": text, "correct": False})
        random.shuffle(options)

        questions.append(
            {
                "type": "vocab",
                "question": f"What is the English translation of: {es_prompt}",
                "category": category,
                "difficulty": "easy",
                "answers": options,
            }
        )

    return questions


def build_quiz_session(trivia_count: int = 5, vocab_count: int = 5) -> list[dict]:
    """Merge trivia and vocab questions for the quiz page."""
    vocab = storage.get_vocab()
    trivia = fetch_trivia(trivia_count)
    vocab_qs = build_vocab_questions(vocab, vocab_count)

    if not trivia and vocab_qs:
        return vocab_qs
    if trivia and not vocab_qs:
        return trivia

    combined = trivia + vocab_qs
    random.shuffle(combined)
    return combined


def score_quiz(questions: list[dict], answers: dict[str, str]) -> tuple[int, int]:
    """Score submitted answers. answers maps question index to answer text."""
    correct = 0
    total = len(questions)
    for idx, q in enumerate(questions):
        chosen = answers.get(str(idx), "")
        for opt in q.get("answers", []):
            if opt.get("text") == chosen and opt.get("correct"):
                correct += 1
                break
    return correct, total

"""Vocabulary selection and answer checking, independent of any interface."""

from dataclasses import dataclass
from pathlib import Path
import math
import random
import re
import unicodedata

import yaml

from .weights import word_weight

LEVELS = ("e", "e1", "e2", "e3", "e4", "e5", "e6",
          "j", "j1", "j2", "j3", "h", "h1", "h2", "h3", "unassigned", "all")


@dataclass(frozen=True)
class Reading:
    text: str
    level: str
    hint: str = ""


@dataclass(frozen=True)
class Question:
    word: str
    readings: tuple[Reading, ...]

    @property
    def answers(self) -> tuple[str, ...]:
        return tuple(reading.text for reading in self.readings)


def normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text.strip())


def check_answer(question: Question, answer: str) -> bool:
    answer = normalize(answer)
    if not answer:
        return False
    if not re.fullmatch(r"[ぁ-ゖゝゞー]+", answer):
        raise ValueError("Enter the reading in hiragana (ひらがな).")
    return answer in question.answers


def load_profiles(path: Path) -> dict[str, str]:
    profiles = yaml.safe_load(path.read_text(encoding="utf-8"))["profiles"]
    if not isinstance(profiles, dict) or not profiles or any(
        not isinstance(k, str) or not k.strip() or not isinstance(v, str) or not v.strip()
        for k, v in profiles.items()
    ):
        raise ValueError("Profiles must map nonempty IDs to display names.")
    return profiles


def load_vocab(path: Path) -> tuple[Question, ...]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    questions = []
    for word, entry in data["vocab"].items():
        readings = []
        for text, value in (entry.get("readings") or {}).items():
            level, hint = value if isinstance(value, list) else (value, "")
            level = "unassigned" if level is None else level
            if level not in LEVELS or level == "all":
                raise ValueError(f"Unknown level {level!r} for {word}.")
            text = normalize(text)
            if not re.fullmatch(r"[ぁ-ゖゝゞー]+", text):
                raise ValueError(f"Invalid hiragana reading for {word}: {text}")
            readings.append(Reading(text, level, hint or ""))
        if readings:
            questions.append(Question(word, tuple(readings)))
    return tuple(questions)


def eligible(vocab: tuple[Question, ...], level: str) -> tuple[Question, ...]:
    if level not in LEVELS:
        raise ValueError(f"Unknown level: {level}")
    # A stage includes its explicitly assigned years; a year never guesses a stage's year.
    def matches(reading: Reading) -> bool:
        return (level == "all" or reading.level == level or
                (level in ("e", "j", "h") and reading.level.startswith(level)))

    # With no sentence context, accept every attested reading of an eligible word.
    return tuple(q for q in vocab if any(matches(r) for r in q.readings))


def make_quiz(vocab: tuple[Question, ...], level: str, count: int,
              history: dict[str, tuple[int, int]] = None) -> list[Question]:
    if count < 1:
        raise ValueError("Question count must be positive.")
    pool = list(eligible(vocab, level))
    if not pool:
        raise ValueError(f"No words assigned to {level}. Run 'levels' to see available choices.")
    history = history or {}
    weighted = []
    for question in pool:
        weight = word_weight(*history.get(question.word, (0, 0)))
        if not math.isfinite(weight) or weight < 0:
            raise ValueError(f"Weight for {question.word} must be finite and nonnegative.")
        if weight > 0:
            weighted.append((question, weight))
    pool = [question for question, _ in weighted]
    weights = [weight for _, weight in weighted]
    selected = []
    for _ in range(min(count, len(pool))):
        index = random.choices(range(len(pool)), weights=weights, k=1)[0]
        selected.append(pool.pop(index))
        weights.pop(index)
    return selected

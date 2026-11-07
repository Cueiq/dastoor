"""The spaCy pipeline a command parses with, and the LLM interface."""

from __future__ import annotations

import spacy

# How each model Dastoor is tested with is installed (pyproject.toml's groups).
INSTALL = {
    "en_core_web_sm": "uv sync",
    "en_core_web_trf": "uv sync --all-groups",
}


class MissingModel(Exception):
    """The model asked for isn't installed."""


def load(name: str):
    try:
        return spacy.load(name)
    except OSError as error:
        # E050: no package or folder of that name.
        if "E050" not in str(error):
            raise
        how = INSTALL.get(name, f"install the spaCy pipeline {name}")
        raise MissingModel(f"the spaCy model {name} isn't installed; to install it: {how}") from None


class CandidateChecker:
    """A small interface for a model that checks candidates."""

    def check(self, point_id: str, sentence: str, words: str, question: str) -> str:
        """Ask the model a short question about a candidate match."""
        raise NotImplementedError


class FakeChecker(CandidateChecker):
    """A fake checker for tests, so they can stand in without a real API."""

    def __init__(self, answers: dict[str, str] | None = None):
        # answers maps f"{point_id}|{sentence}" to a mocked string answer
        self.answers = answers or {}

    def check(self, point_id: str, sentence: str, words: str, question: str) -> str:
        key = f"{point_id}|{sentence}"
        return self.answers.get(key, "unclear (fake check)")

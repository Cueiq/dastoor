"""Checkers to resolve the meaning of candidate points."""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Protocol

from .points import Point


class CandidateChecker(Protocol):
    def check(self, point: Point, sentence: str, words: str) -> str:
        ...


class FakeChecker:
    """A fake checker for tests. Raises KeyError on unknown matches."""

    def __init__(self, answers: dict[str, str]):
        # answers maps "point_id|sentence|words" to a mocked answer
        self.answers = answers

    def check(self, point: Point, sentence: str, words: str) -> str:
        key = f"{point.id}|{sentence}|{words}"
        if key not in self.answers:
            raise KeyError(f"FakeChecker has no answer for: {key}")
        return self.answers[key]


class LLMChecker:
    """A real language model checker using OpenAI's API."""

    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

    def check(self, point: Point, sentence: str, words: str) -> str:
        if not point.check_question:
            return "unclear"

        prompt = (
            f"Sentence: \"{sentence}\"\n"
            f"Phrase: \"{words}\"\n"
            f"Question: {point.check_question}\n"
            "Answer briefly in 1 to 3 words."
        )

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps({
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
            }).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
        )

        try:
            with urllib.request.urlopen(req) as response:
                body = json.loads(response.read())
                # Return lowercase exact answer (e.g. "guess" or "obligation")
                return body["choices"][0]["message"]["content"].strip().lower()
        except Exception as e:
            # Handle errors per line without crashing the whole process
            print(f"Error checking {point.id} on '{words}': {e}")
            return "error"

"""Asking a model what a candidate means (#1).

A point whose words can't settle its meaning has a `check` in its file: a
question, the answers it allows, and the answer that says the point is
there (`must` is a guess or an obligation; `must-guess` keeps "guess"). A
checker asks the question about one match, and gives back one of the
answers, or "unclear" when the reply names none of them or more than one.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Protocol

from .points import Point

UNCLEAR = "unclear"
OPENAI = "https://api.openai.com/v1"
TIMEOUT_S = 60


class CheckFailed(Exception):
    """The model couldn't be asked: no key, no server, no answer."""


class Checker(Protocol):
    def check(self, point: Point, sentence: str, words: str) -> str: ...


def answer_in(reply: str, answers: list[str]) -> str:
    """The one allowed answer a reply names, or "unclear". A model that
    thinks aloud (<think>…</think>) is read after its thinking."""
    reply = re.sub(r"<think>.*?</think>", " ", reply, flags=re.DOTALL | re.IGNORECASE)
    said = set(re.findall(r"[a-z]+", reply.lower()))
    named = [answer for answer in answers if answer in said]
    return named[0] if len(named) == 1 else UNCLEAR


def keeps(point: Point, answer: str) -> bool:
    """Whether a checked match stays: the answer says the point is there,
    or the model couldn't tell and the point's rule is trusted to tag."""
    assert point.check is not None
    return answer == point.check.keep or (answer == UNCLEAR and point.tag)


def prompt(point: Point, sentence: str, words: str) -> str:
    assert point.check is not None
    return (
        f'Sentence: "{sentence}"\n'
        f'Words: "{words}"\n'
        f"{point.check.question}\n"
        f"Answer with one word: {' or '.join(point.check.answers)}."
    )


class FakeChecker:
    """For tests: answers by "point|sentence|words", and fails on any match
    it wasn't given, so a test also shows what was asked."""

    def __init__(self, answers: dict[str, str]):
        self.answers = answers
        self.asked: list[str] = []

    def check(self, point: Point, sentence: str, words: str) -> str:
        key = f"{point.id}|{sentence}|{words}"
        self.asked.append(key)
        if key not in self.answers:
            raise KeyError(f"FakeChecker has no answer for: {key}")
        assert point.check is not None
        return answer_in(self.answers[key], point.check.answers)


class LLMChecker:
    """Any OpenAI-compatible chat API: OpenAI's by default (OPENAI_API_KEY),
    or another server by DASTOOR_CHECK_URL, such as a local Ollama
    (http://localhost:11434/v1, no key). DASTOOR_CHECK_MODEL names the
    model. Each match's sentence is sent to that server."""

    def __init__(self):
        self.url = os.environ.get("DASTOOR_CHECK_URL", OPENAI).rstrip("/")
        self.model = os.environ.get("DASTOOR_CHECK_MODEL", "gpt-4o-mini")
        self.key = os.environ.get("OPENAI_API_KEY")
        if self.url == OPENAI and not self.key:
            raise CheckFailed(
                "--check needs OPENAI_API_KEY, or DASTOOR_CHECK_URL for another OpenAI-compatible server"
            )
        # The same sentence and words are asked about once.
        self.answers: dict[tuple[str, str, str], str] = {}

    def check(self, point: Point, sentence: str, words: str) -> str:
        assert point.check is not None
        key = (point.id, sentence, words)
        if key not in self.answers:
            self.answers[key] = answer_in(self.ask(prompt(point, sentence, words)), point.check.answers)
        return self.answers[key]

    def ask(self, text: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        body = json.dumps(
            {"model": self.model, "messages": [{"role": "user", "content": text}], "temperature": 0}
        ).encode()
        request = urllib.request.Request(f"{self.url}/chat/completions", data=body, headers=headers)
        # One more try for a dropped connection or a busy server; a refused
        # key or an unknown model fails at once, as every line would.
        for attempt in (1, 2):
            try:
                with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
                    return json.loads(response.read())["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as error:
                if error.code < 500 or attempt == 2:
                    raise CheckFailed(f"{self.url} answered {error.code} {error.reason}") from None
            except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
                if attempt == 2:
                    raise CheckFailed(f"couldn't reach {self.url}: {getattr(error, 'reason', error)}") from None
            except (KeyError, IndexError, TypeError, ValueError):
                raise CheckFailed(f"{self.url} sent no answer the check can read") from None
            time.sleep(2)
        raise AssertionError("unreachable")

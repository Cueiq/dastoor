"""The points: one YAML file each, in `points/`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .rules import Found, Rules

POINTS = Path(__file__).resolve().parents[2] / "points"

# Where a book shows a point beyond its topic (`place:` in its file): on the
# tenses' timeline, by the kind of action and when it is (an action lasting
# up to now is between past and now), and under what a learner wants to do
# with a sentence.
TIMELINE_ROWS = ("once", "ongoing", "up-to-now", "habit", "passive")
TIMELINE_WHEN = ("past", "now", "future")
GOALS = ("ask", "need", "able", "guess", "if", "compare", "emphasise", "combine-verbs", "report", "passive", "everyday")


@dataclass
class Point:
    id: str
    title: dict
    topic: str
    cefrj: list[str]
    match: list[dict]
    exclude: list[dict] = field(default_factory=list)
    # The rule can't settle what the words mean: its matches are candidates.
    needs_meaning: bool = False
    # Whether `tag` marks it: a rule right too rarely misleads.
    tag: bool = True
    # Other ids the guides gave the same point, for scoring against them.
    aliases: list[str] = field(default_factory=list)
    # What a learner may search it by, in English and Persian.
    keywords: list[str] = field(default_factory=list)
    # Its place on a book's timeline and among its goals.
    place: dict = field(default_factory=dict)
    tests: dict = field(default_factory=dict)
    rules: Rules | None = None

    def find(self, doc) -> list[Found]:
        assert self.rules is not None, "load the point with a pipeline"
        return self.rules.find(doc)


def _no_booleans(value, where: str) -> None:
    """YAML reads an unquoted no, yes, on or off as true or false: a word
    must be quoted to be a word. A Matcher flag (IS_SENT_START, IS_PUNCT…)
    is the one place true or false is meant."""
    if isinstance(value, bool):
        raise ValueError(f"{where}: {value} where a word should be; quote it (\"no\")")
    if isinstance(value, dict):
        for key, each in value.items():
            if str(key).startswith("IS_") and isinstance(each, bool):
                continue
            _no_booleans(each, f"{where}.{key}")
    if isinstance(value, list):
        for at, each in enumerate(value):
            _no_booleans(each, f"{where}[{at}]")


def check_place(place, where: str) -> None:
    """A point's place: a timeline row (and, but for up-to-now, when), and a
    goal, each one the book knows; either may be left out."""
    if not place:
        return
    unknown = set(place) - {"timeline", "goal"}
    if unknown:
        raise ValueError(f"{where}: place has {sorted(unknown)}; it takes timeline and goal")
    timeline = place.get("timeline")
    if timeline is not None:
        row, when = timeline.get("row"), timeline.get("when")
        if row not in TIMELINE_ROWS:
            raise ValueError(f"{where}: timeline row {row!r} isn't one of {TIMELINE_ROWS}")
        if row == "up-to-now" and when is not None:
            raise ValueError(f"{where}: up-to-now is between past and now: no when")
        if row != "up-to-now" and when not in TIMELINE_WHEN:
            raise ValueError(f"{where}: timeline when {when!r} isn't one of {TIMELINE_WHEN}")
    goal = place.get("goal")
    if goal is not None and goal not in GOALS:
        raise ValueError(f"{where}: goal {goal!r} isn't one of {GOALS}")


def load(nlp, folder: Path = POINTS, only: set[str] | None = None) -> list[Point]:
    points = []
    for path in sorted(folder.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        if data["id"] != path.stem:
            raise ValueError(f"{path.name}: its id is {data['id']}")
        _no_booleans(data.get("match"), f"{path.name}: match")
        _no_booleans(data.get("exclude"), f"{path.name}: exclude")
        check_place(data.get("place"), path.name)
        if only and data["id"] not in only:
            continue
        point = Point(
            id=data["id"],
            title=data.get("title", {}),
            topic=data.get("topic", ""),
            cefrj=[str(item) for item in data.get("cefrj", [])],
            match=data["match"],
            exclude=data.get("exclude", []),
            needs_meaning=bool(data.get("needs_meaning", False)),
            tag=bool(data.get("tag", True)),
            aliases=list(data.get("aliases", [])),
            keywords=[str(word) for word in data.get("keywords", [])],
            place=data.get("place", {}),
            tests=data.get("tests", {}),
        )
        point.rules = Rules(point.id, point.match, point.exclude, nlp.vocab)
        points.append(point)
    return points

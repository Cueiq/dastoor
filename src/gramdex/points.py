"""The points: one YAML file each, in `points/`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .rules import Found, Rules

POINTS = Path(__file__).resolve().parents[2] / "points"


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
    tests: dict = field(default_factory=dict)
    rules: Rules | None = None

    def find(self, doc) -> list[Found]:
        assert self.rules is not None, "load the point with a pipeline"
        return self.rules.find(doc)


def _no_booleans(value, where: str) -> None:
    """YAML reads an unquoted no, yes, on or off as true or false: a word
    must be quoted to be a word."""
    if isinstance(value, bool):
        raise ValueError(f"{where}: {value} where a word should be; quote it (\"no\")")
    if isinstance(value, dict):
        for key, each in value.items():
            _no_booleans(each, f"{where}.{key}")
    if isinstance(value, list):
        for at, each in enumerate(value):
            _no_booleans(each, f"{where}[{at}]")


def load(nlp, folder: Path = POINTS, only: set[str] | None = None) -> list[Point]:
    points = []
    for path in sorted(folder.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        if data["id"] != path.stem:
            raise ValueError(f"{path.name}: its id is {data['id']}")
        _no_booleans(data.get("match"), f"{path.name}: match")
        _no_booleans(data.get("exclude"), f"{path.name}: exclude")
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
            tests=data.get("tests", {}),
        )
        point.rules = Rules(point.id, point.match, point.exclude, nlp.vocab)
        points.append(point)
    return points

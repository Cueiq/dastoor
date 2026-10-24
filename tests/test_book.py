"""A point's place in a book, and how often it is heard. Run with the small
model: `uv run python -m unittest`."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from dastoor import heard, model, points


class Place(unittest.TestCase):
    def test_every_point_has_a_place_the_book_knows(self):
        for path in sorted(points.POINTS.glob("*.yaml")):
            place = yaml.safe_load(path.read_text()).get("place") or {}
            points.check_place(place, path.name)
            self.assertTrue(place.get("timeline") or place.get("goal"), f"{path.name} is nowhere in the book")

    def test_a_place_the_book_doesnt_know_is_refused(self):
        refused = [
            {"timeline": {"row": "sometimes", "when": "past"}},
            {"timeline": {"row": "habit"}},
            {"timeline": {"row": "up-to-now", "when": "now"}},
            {"goal": "dance"},
            {"shelf": "top"},
        ]
        for place in refused:
            with self.subTest(place=place), self.assertRaises(ValueError):
                points.check_place(place, "x.yaml")


class Heard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nlp = model.load("en_core_web_sm")
        cls.points = points.load(cls.nlp, only={"be-going-to", "will", "would-past-habit"})

    def test_each_sentence_counts_once_however_often_it_is_said(self):
        cue = "{n}\n00:00:0{n},000 --> 00:00:0{n},900\n{text}\n"
        lines = [
            "I'm going to call her.",
            "It will rain later, I think.",
            "We're going to win this.",
            "Fine.",
            # Enough English for the file to be read as English.
            "This is a long line of plain English words. " * 6,
        ]
        with tempfile.TemporaryDirectory() as folder:
            body = "\n".join(cue.format(n=at + 1, text=text) for at, text in enumerate(lines))
            # The same episode twice, and a Persian file beside it.
            Path(folder, "one.srt").write_text(body)
            Path(folder, "copy.srt").write_text(body)
            Path(folder, "one.fa.srt").write_text("1\n00:00:01,000 --> 00:00:01,900\nسلام\n")
            files = heard.subtitle_files([Path(folder)])
            counted = heard.count(self.nlp, self.points, files)
        self.assertEqual([path.name for path in files], ["copy.srt", "one.srt"])
        self.assertEqual(counted["points"]["be-going-to"], 2)
        self.assertEqual(counted["points"]["will"], 1)
        # Points not tagged aren't counted.
        self.assertNotIn("would-past-habit", counted["points"])

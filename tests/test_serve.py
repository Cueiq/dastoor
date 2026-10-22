"""`dastoor serve`: a text a line in, its marks a line out, the model loaded
once. Run with the small model: `uv run python -m unittest`."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest


class Serve(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.process = subprocess.Popen(
            [sys.executable, "-m", "dastoor.cli", "serve"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
        )
        cls.ready = json.loads(cls.process.stdout.readline())

    @classmethod
    def tearDownClass(cls):
        cls.process.stdin.close()
        cls.process.wait(timeout=30)

    def ask(self, line: str) -> dict:
        self.process.stdin.write(line + "\n")
        self.process.stdin.flush()
        return json.loads(self.process.stdout.readline())

    def test_it_says_when_it_is_ready(self):
        self.assertTrue(self.ready["ready"])
        self.assertEqual(self.ready["model"], "en_core_web_sm")
        self.assertGreater(self.ready["points"], 30)

    def test_a_text_s_points_come_with_their_words_and_where_they_are(self):
        text = "I've been trying to get a hold of you, so don't tell me you were busy."
        answer = self.ask(json.dumps({"id": 7, "text": text}))
        self.assertEqual(answer["id"], 7)
        found = {mark["point"]: mark for mark in answer["points"]}
        self.assertEqual({"present-perfect-continuous", "verb-to-infinitive", "dont-imperative"} - found.keys(), set())
        for mark in answer["points"]:
            self.assertEqual(text[mark["start"] : mark["end"]], mark["words"])
        self.assertFalse(found["dont-imperative"]["candidate"])

    def test_offsets_count_characters_beyond_ascii(self):
        text = "“Well,” she said — I'm going to call her."
        answer = self.ask(json.dumps({"id": "q", "text": text}))
        going = [mark for mark in answer["points"] if mark["point"] == "be-going-to"]
        self.assertTrue(going)
        self.assertEqual(text[going[0]["start"] : going[0]["end"]], going[0]["words"])

    def test_a_meaning_point_is_a_candidate(self):
        answer = self.ask(json.dumps({"text": "You must be tired."}))
        self.assertIsNone(answer["id"])
        self.assertTrue(any(mark["candidate"] for mark in answer["points"]))

    def test_its_sentences_are_given(self):
        text = "I'm tired. Let's go home."
        answer = self.ask(json.dumps({"text": text}))
        self.assertEqual([text[a:b].strip() for a, b in answer["sentences"]], ["I'm tired.", "Let's go home."])

    def test_a_bad_request_is_answered_and_the_next_still_is(self):
        self.assertIn("error", self.ask("not json"))
        self.assertIn("error", self.ask(json.dumps({"id": 1})))
        self.assertEqual(self.ask(json.dumps({"id": 2, "text": ""}))["points"], [])


if __name__ == "__main__":
    unittest.main()

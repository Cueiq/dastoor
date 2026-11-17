import argparse
import contextlib
import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from dastoor import check, cli

SRT = """1
00:00:01,000 --> 00:00:02,000
He must be tired.

2
00:00:03,000 --> 00:00:04,000
You must be quiet in here.

3
00:00:05,000 --> 00:00:06,000
When I was a kid, we would go fishing every Sunday.

4
00:00:07,000 --> 00:00:08,000
She's going to call you.
"""

# Every match --check asks about in SRT, and nothing else: FakeChecker fails
# on a match it has no answer for.
ANSWERS = {
    "must-guess|He must be tired.|must be": "Guess.",
    "must-guess|You must be quiet in here.|must be": "It's an obligation.",
    "would-past-habit|When I was a kid, we would go fishing every Sunday.|would go": "habit",
}


def tagged(checker=None, check_flag=False) -> dict[int, list[dict]]:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "episode.srt"
        path.write_text(SRT)
        args = argparse.Namespace(model="en_core_web_sm", file=str(path), json=True, all=False, check=check_flag)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli.tag(args, checker=checker)
    return {line["cue"]: line["points"] for line in json.loads(out.getvalue())["lines"]}


class AnswerTest(unittest.TestCase):
    def test_a_reply_is_read_down_to_one_allowed_answer(self):
        answers = ["guess", "obligation"]
        self.assertEqual(check.answer_in("Guess.", answers), "guess")
        self.assertEqual(check.answer_in("It's an Obligation.", answers), "obligation")
        self.assertEqual(check.answer_in("<think>guess? or obligation?</think>\nobligation", answers), "obligation")
        self.assertEqual(check.answer_in("Either a guess or an obligation.", answers), check.UNCLEAR)
        self.assertEqual(check.answer_in("I don't know.", answers), check.UNCLEAR)


class TagCheckTest(unittest.TestCase):
    def test_the_answer_keeps_or_drops_each_match(self):
        checker = check.FakeChecker(ANSWERS)
        lines = tagged(checker)
        self.assertEqual(sorted(checker.asked), sorted(ANSWERS))
        # A guess stays, settled; an obligation isn't must-guess.
        self.assertEqual(
            [(each["point"], each["answer"], each["candidate"]) for each in lines[1]],
            [("must-guess", "guess", False)],
        )
        self.assertNotIn(2, lines)
        # would for a past habit is tagged only through the check.
        self.assertEqual([each["point"] for each in lines[3]], ["would-past-habit"])
        # A point without a check is tagged as before, and never asked about.
        self.assertEqual([(each["point"], "answer" in each) for each in lines[4]], [("be-going-to", False)])

    def test_without_check_nothing_is_asked_and_would_isnt_tagged(self):
        lines = tagged()
        self.assertEqual([each["point"] for each in lines[2]], ["must-guess"])
        self.assertNotIn(3, lines)

    def test_unclear_keeps_a_tagged_point_as_a_candidate(self):
        answers = {key: "no idea" for key in ANSWERS}
        lines = tagged(check.FakeChecker(answers))
        self.assertEqual([(each["answer"], each["candidate"]) for each in lines[1]], [("unclear", True)])
        self.assertNotIn(3, lines)


class FailureTest(unittest.TestCase):
    def run_main(self, argv, env):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, env, clear=False), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_no_key_is_said_plainly(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "episode.srt"
            path.write_text(SRT)
            with mock.patch.dict(os.environ, {}, clear=True):
                code, out, err = self.run_main(["tag", str(path), "--check"], {})
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("--check needs OPENAI_API_KEY", err)

    def test_a_server_that_cant_be_reached_leaves_stdout_clean(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "episode.srt"
            path.write_text(SRT)
            refused = urllib.error.URLError("connection refused")
            with mock.patch("urllib.request.urlopen", side_effect=refused), mock.patch("time.sleep"):
                code, out, err = self.run_main(
                    ["tag", str(path), "--json", "--check"], {"DASTOOR_CHECK_URL": "http://localhost:1/v1"}
                )
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("couldn't reach http://localhost:1/v1", err)


if __name__ == "__main__":
    unittest.main()

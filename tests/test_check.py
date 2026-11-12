import argparse
import unittest
from unittest.mock import patch, MagicMock

from dastoor.check import FakeChecker
from dastoor.points import Point
from dastoor.cli import tag


class TestFakeChecker(unittest.TestCase):
    def test_answers_from_map_and_raises(self):
        point = Point(id="must-guess", title={}, topic="", cefrj=[], match=[])
        checker = FakeChecker({"must-guess|He must be tired.|must": "guess"})

        # Test valid answer
        ans = checker.check(point, "He must be tired.", "must")
        self.assertEqual(ans, "guess")

        # Test unknown key raises KeyError as requested
        with self.assertRaises(KeyError):
            checker.check(point, "He must go.", "must")

    @patch("dastoor.cli.check_module.LLMChecker")
    @patch("dastoor.cli.pieces")
    @patch("dastoor.cli.read")
    @patch("dastoor.cli.points_module.load")
    @patch("dastoor.cli.model_module.load")
    def test_tag_check_records_answer(self, mock_model_load, mock_points_load, mock_read, mock_pieces, mock_llm_class):
        # Create a mock point that needs meaning
        point = Point(id="must-guess", title={}, topic="", cefrj=[], match=[])
        point.tag = True
        point.needs_meaning = True
        point.check_question = "Is it guess or obligation?"

        # We need a mock to bypass the spaCy match logic in find()
        class MockMatch:
            start = 0
            end = 1
            form = "must"

        point.find = lambda doc: [MockMatch()]

        mock_points_load.return_value = [point]

        # Mock nlp and doc behavior so spaCy isn't actually needed
        mock_doc = MagicMock()
        mock_span = MagicMock()
        mock_span.text = "He"
        mock_span.start_char = 0
        mock_span.end_char = 2
        mock_doc.__getitem__.return_value = mock_span

        mock_nlp = MagicMock(return_value=mock_doc)
        mock_model_load.return_value = mock_nlp

        # Mock subtitles chunks processing
        mock_piece = MagicMock()
        mock_piece.text = "He must be tired."
        mock_piece.cues.return_value = [1]
        mock_pieces.return_value = [mock_piece]

        # Mock the input file lines
        class MockLine:
            cue = 1
            said = ["He must be tired."]

        mock_read.return_value = [MockLine()]

        # Setup the FakeChecker instead of LLMChecker
        fake_checker = FakeChecker({"must-guess|He must be tired.|He": "guess"})
        mock_llm_class.return_value = fake_checker

        # Build args for dastoor tag --check
        args = argparse.Namespace(file="fake.srt", model="fake", check=True, json=False, all=False)

        # Run tag and intercept stdout
        with patch('sys.stdout') as mock_stdout:
            from io import StringIO
            import sys
            sys.stdout = StringIO()
            tag(args)
            output = sys.stdout.getvalue()
            sys.stdout = mock_stdout

        # The answer "guess" should be recorded beside the match in the output
        self.assertIn("must-guess «He» [guess]", output)

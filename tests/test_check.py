import unittest
from dastoor.model import FakeChecker


class TestFakeChecker(unittest.TestCase):
    def test_answers_from_map(self):
        checker = FakeChecker({"must-guess|He must be tired.": "guess"})
        ans = checker.check("must-guess", "He must be tired.", "must", "Is it guess or obligation?")
        self.assertEqual(ans, "guess")

    def test_fallback_unclear(self):
        checker = FakeChecker()
        ans = checker.check("must-guess", "He must go.", "must", "Is it guess or obligation?")
        self.assertEqual(ans, "unclear (fake check)")
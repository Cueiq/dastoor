import unittest
from dastoor.subtitles import Line, pieces

class TestSubtitles(unittest.TestCase):
    def test_pieces_joins_trailing_off_into_capitalized_continuation(self):
        lines = [
            Line(1, 0, "", ["If H isn't for Howard..."]),
            Line(2, 0, "", ["Then H is for Hector!"]),
        ]
        out = pieces(lines)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].text, "If H isn't for Howard Then H is for Hector!")

    def test_pieces_joins_no_stop_into_capitalized_continuation(self):
        lines = [
            Line(1, 0, "", ["I went to the store"]),
            Line(2, 0, "", ["And I bought some milk."]),
        ]
        out = pieces(lines)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].text, "I went to the store And I bought some milk.")

    def test_pieces_does_not_join_no_stop_into_independent_sentence(self):
        lines = [
            Line(1, 0, "", ["I am going home"]),
            Line(2, 0, "", ["What about you?"]),
        ]
        out = pieces(lines)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0].text, "I am going home")
        self.assertEqual(out[1].text, "What about you?")

if __name__ == "__main__":
    unittest.main()
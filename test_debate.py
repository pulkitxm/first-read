import unittest

from debate import build_debate, match_preset
from readthrough import ScriptError


class DebateTests(unittest.TestCase):
    def test_preset_uses_two_distinct_voices(self):
        debate = build_debate("Should remote work be the default?", 2)
        names = [row["name"] for row in debate["lines"]]
        self.assertEqual(names[0], "Mira")
        self.assertIn("Owen", names)
        self.assertNotIn("Priya", names)
        voices = {row["name"]: row["voice"] for row in debate["cast"]}
        self.assertEqual(voices["Mira"], "Sheila")
        self.assertEqual(voices["Owen"], "Adrian")
        self.assertGreaterEqual(len(debate["lines"]), 6)

    def test_three_voices_on_the_phone_preset(self):
        debate = build_debate("phones", 3)
        names = {row["name"] for row in debate["lines"]}
        self.assertEqual(names, {"Mira", "Owen", "Priya"})
        self.assertEqual(len({row["voice"] for row in debate["cast"]}), 3)

    def test_unknown_topic_still_debates(self):
        debate = build_debate("Should cities ban cars on Sundays?", 2)
        self.assertIsNone(match_preset("Should cities ban cars on Sundays?"))
        blob = " ".join(line["text"] for line in debate["lines"])
        self.assertIn("cities ban cars", blob)
        self.assertGreaterEqual(len(debate["lines"]), 6)

    def test_extra_round_grows_the_preset(self):
        base = build_debate("Tabs or spaces?", 2)
        more = build_debate("Tabs or spaces?", 2, extra_rounds=1)
        self.assertGreater(len(more["lines"]), len(base["lines"]))

    def test_rejects_bad_input(self):
        with self.assertRaises(ScriptError):
            build_debate("   ", 2)
        with self.assertRaises(ScriptError):
            build_debate("Remote work", 1)


if __name__ == "__main__":
    unittest.main()

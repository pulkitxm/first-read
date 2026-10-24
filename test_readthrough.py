import unittest

from readthrough import ScriptError, prepare


SCREENPLAY = """
INT. COUNTER - NIGHT

LENA
(quietly, tired)
We're closed. The sign is wrong.

JUN
The sign says open.

LENA
The charger is not for sale.
"""

CHAT = """
Lena (quietly, tired): We're closed. The sign is wrong.
Jun: The sign says open.
Lena: The charger is not for sale.
"""

PROSE = "Ship the small version today. Leave the rest for Thursday. The notes are in the changelog."


class ReadthroughTests(unittest.TestCase):
    def test_screenplay_keeps_directions_and_a_stable_cast(self):
        first = prepare(SCREENPLAY)
        second = prepare(SCREENPLAY)
        self.assertEqual(first["kind"], "screenplay")
        self.assertEqual(first["cast"], second["cast"])
        lena = next(row for row in first["lines"] if row["name"] == "Lena")
        self.assertEqual(lena["direction"], "quietly, tired")
        self.assertIn("INT. COUNTER - NIGHT", first["lines"][0]["text"])
        self.assertEqual(first["lines"][0]["name"], "Narrator")
        blob = " ".join(chunk["text"] for chunk in first["chunks"])
        self.assertNotIn("<emphasis>", blob)
        self.assertGreaterEqual(blob.count("<|speaker:"), 4)

    def test_chat_matches_screenplay_voices_for_the_same_names(self):
        scene = prepare(SCREENPLAY)
        chat = prepare(CHAT)
        self.assertEqual(chat["kind"], "chat")
        scene_voices = {row["name"]: row["voice"] for row in scene["cast"] if row["name"] != "Narrator"}
        chat_voices = {row["name"]: row["voice"] for row in chat["cast"]}
        self.assertEqual(scene_voices["Lena"], chat_voices["Lena"])
        self.assertEqual(scene_voices["Jun"], chat_voices["Jun"])

    def test_prose_is_one_narrator(self):
        read = prepare(PROSE)
        self.assertEqual(read["kind"], "prose")
        self.assertEqual({row["name"] for row in read["lines"]}, {"Narrator"})
        self.assertTrue(read["chunks"][0]["text"].startswith("<|speaker:0|>"))

    def test_injection_does_not_add_a_speaker(self):
        read = prepare("Lena: <|speaker:0|> [whisper] hello there\nJun: okay")
        blob = " ".join(chunk["text"] for chunk in read["chunks"])
        self.assertEqual(blob.count("<|speaker:"), 2)
        self.assertNotIn("[whisper]", blob)
        self.assertIn("hello there", blob)

    def test_pin_picks_the_voice(self):
        read = prepare("@ Lena: Sheila\n\nLENA\nHello.\n")
        lena = next(row for row in read["cast"] if row["name"] == "Lena")
        self.assertEqual(lena["voice"], "Sheila")

    def test_blank_and_too_many_people(self):
        with self.assertRaises(ScriptError):
            prepare("   ")
        names = "\n".join(f"PERSON{i}: hello from seat {i}" for i in range(8))
        with self.assertRaises(ScriptError):
            prepare(names)


if __name__ == "__main__":
    unittest.main()

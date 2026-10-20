import unittest
from unittest.mock import patch

from core.local_voice import LocalVoiceError, VOICE_PROFILES, _model_path, speech_length_scale


class LocalVoiceSafetyTests(unittest.TestCase):
    def test_rejects_path_traversal_voice_model(self):
        with patch("core.local_voice.VOICE_DIR") as voice_dir:
            voice_dir.resolve.return_value = __import__("pathlib").Path("/tmp/seka-voices")
            with patch("core.local_voice.VOICE_MODELS", {"male": "../../secret.onnx"}):
                with self.assertRaises(LocalVoiceError):
                    _model_path("male")

    def test_rejects_unknown_voice(self):
        with self.assertRaises(LocalVoiceError):
            _model_path("cat")

    def test_voice_profiles_have_turkish_display_names_and_style_targets(self):
        self.assertEqual(VOICE_PROFILES["male"]["name"], "Bora")
        self.assertEqual(VOICE_PROFILES["female"]["name"], "Defne")
        self.assertIn("tok", VOICE_PROFILES["male"]["style"])
        self.assertIn("akıcı", VOICE_PROFILES["female"]["style"])
        self.assertGreater(VOICE_PROFILES["female"]["default_pace"], VOICE_PROFILES["male"]["default_pace"])

    def test_voice_profiles_have_distinct_pacing(self):
        self.assertGreater(speech_length_scale("male", 1.0), speech_length_scale("female", 1.0))
        self.assertLess(speech_length_scale("male", 1.15), speech_length_scale("male", 1.0))

    def test_speech_pace_is_bounded(self):
        for pace in (0.5, 1.5, float("nan"), "fast"):
            with self.subTest(pace=pace):
                with self.assertRaises(LocalVoiceError):
                    speech_length_scale("male", pace)


if __name__ == "__main__":
    unittest.main()

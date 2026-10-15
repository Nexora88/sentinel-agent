import unittest
from unittest.mock import patch

from core.local_voice import LocalVoiceError, _model_path


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


if __name__ == "__main__":
    unittest.main()

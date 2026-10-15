import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from web import app as web_app


class WebDegradationTests(unittest.TestCase):
    def test_health_endpoint_does_not_initialize_ollama_or_rag(self):
        with patch.object(web_app, "get_pipeline", side_effect=AssertionError("must stay lazy")):
            result = asyncio.run(web_app.health())
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["model_checked"])

    def test_chat_returns_turkish_recovery_message_if_pipeline_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            old_history = web_app.chat_history
            web_app.chat_history = {}
            try:
                with patch.object(web_app, "CHAT_HISTORY_FILE", Path(directory) / "history.json"), \
                     patch.object(web_app, "get_user", return_value={"username": "owner"}), \
                     patch.object(web_app, "get_pipeline", side_effect=RuntimeError("model unavailable")):
                    result = asyncio.run(
                        web_app.api_chat(
                            web_app.ChatRequest(message="Merhaba"),
                            authorization="Bearer test",
                        )
                    )
                self.assertIn("Ollama/model bağlantısı hazır değil", result["reply"])
                self.assertTrue((Path(directory) / "history.json").is_file())
            finally:
                web_app.chat_history = old_history


if __name__ == "__main__":
    unittest.main()

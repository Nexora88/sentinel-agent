import os
import unittest
from unittest.mock import patch

from core.ollama_client import OllamaClient


class MkaosClientRoutingTests(unittest.TestCase):
    def test_mkaos_is_disabled_by_default_and_ollama_remains_chat_provider(self):
        with patch.dict(os.environ, {}, clear=True):
            client = OllamaClient(model="test-model")
        self.assertFalse(client.mkaos_enabled)
        self.assertEqual(client.chat_base_url, "http://localhost:11434")
        self.assertEqual(client.base_url, "http://localhost:11434")
        self.assertEqual(client.model_name, "test-model")

    def test_mkaos_opt_in_routes_chat_but_keeps_ollama_embeddings(self):
        env = {
            "MKAOS_ENABLED": "true",
            "MKAOS_BASE_URL": "http://127.0.0.1:11435",
            "MKAOS_MODEL_NAME": "mkaos-local",
            "OLLAMA_BASE_URL": "http://localhost:11434",
        }
        with patch.dict(os.environ, env, clear=True):
            client = OllamaClient(model="qwen2.5:7b", embed_model="nomic-embed-text")
        self.assertTrue(client.mkaos_enabled)
        self.assertEqual(client.chat_base_url, "http://127.0.0.1:11435")
        self.assertEqual(client.base_url, "http://localhost:11434")
        self.assertEqual(client.model_name, "mkaos-local")
        self.assertEqual(client.embed_model_name, "nomic-embed-text")

    def test_mkaos_remote_endpoint_is_rejected(self):
        with patch.dict(os.environ, {
            "MKAOS_ENABLED": "true",
            "MKAOS_BASE_URL": "https://remote.example.com",
        }, clear=True):
            with self.assertRaises(ValueError):
                OllamaClient()


if __name__ == "__main__":
    unittest.main()

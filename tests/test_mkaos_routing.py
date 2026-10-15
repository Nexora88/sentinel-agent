import os
import unittest
from unittest.mock import patch

from core.ollama_client import OllamaClient, validate_local_ollama_url


class MkaosRoutingTests(unittest.TestCase):
    def test_named_mkaos_service_is_allowed_for_internal_compose_network(self):
        self.assertEqual(
            validate_local_ollama_url("http://mkaos:11435"),
            "http://mkaos:11435",
        )

    def test_mkaos_opt_in_routes_chat_but_keeps_embeddings_on_ollama(self):
        env = {
            "MKAOS_ENABLED": "true",
            "MKAOS_BASE_URL": "http://mkaos:11435",
            "MKAOS_MODEL_NAME": "mkaos-local",
            "OLLAMA_BASE_URL": "http://ollama:11434",
            "OLLAMA_MODEL": "qwen2.5:7b",
            "OLLAMA_EMBED_MODEL": "nomic-embed-text",
        }
        with patch.dict(os.environ, env, clear=False):
            client = OllamaClient()
        self.assertEqual(client.chat_base_url, "http://mkaos:11435")
        self.assertEqual(client.model_name, "mkaos-local")
        self.assertEqual(client.base_url, "http://ollama:11434")
        self.assertEqual(client.embed_model_name, "nomic-embed-text")

    def test_mkaos_disabled_rolls_chat_back_to_ollama(self):
        env = {
            "MKAOS_ENABLED": "false",
            "MKAOS_BASE_URL": "http://mkaos:11435",
            "OLLAMA_BASE_URL": "http://ollama:11434",
            "OLLAMA_MODEL": "qwen2.5:7b",
        }
        with patch.dict(os.environ, env, clear=False):
            client = OllamaClient()
        self.assertEqual(client.chat_base_url, "http://ollama:11434")
        self.assertEqual(client.model_name, "qwen2.5:7b")

    def test_remote_model_endpoints_remain_rejected(self):
        with self.assertRaises(ValueError):
            validate_local_ollama_url("http://example.com:11435")


if __name__ == "__main__":
    unittest.main()

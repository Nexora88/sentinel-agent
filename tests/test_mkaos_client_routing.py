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

    def test_chat_invokes_only_the_opted_in_mkaos_endpoint(self):
        from unittest.mock import Mock
        from langchain_core.messages import HumanMessage, SystemMessage
        response = Mock(content="Merhaba")
        llm = Mock()
        llm.invoke.return_value = response
        with patch.dict(os.environ, {
            "MKAOS_ENABLED": "true",
            "MKAOS_BASE_URL": "http://127.0.0.1:11435",
            "MKAOS_MODEL_NAME": "mkaos-local",
            "OLLAMA_BASE_URL": "http://localhost:11434",
        }, clear=True), patch("core.ollama_client.ChatOllama", return_value=llm) as factory:
            client = OllamaClient()
            answer = client.chat("Merhaba", system="Türkçe yanıt ver.")
        self.assertEqual(answer, "Merhaba")
        factory.assert_called_once_with(
            model="mkaos-local", base_url="http://127.0.0.1:11435", temperature=0.15,
            repeat_penalty=1.1, top_p=0.9
        )
        messages = llm.invoke.call_args.args[0]
        self.assertIsInstance(messages[0], SystemMessage)
        self.assertIsInstance(messages[1], HumanMessage)

    def test_mkaos_runtime_failure_is_visible_and_never_silently_falls_back(self):
        from unittest.mock import Mock
        llm = Mock()
        llm.invoke.side_effect = RuntimeError("MKAOS is unavailable")
        with patch.dict(os.environ, {
            "MKAOS_ENABLED": "true",
            "MKAOS_BASE_URL": "http://127.0.0.1:11435",
            "OLLAMA_BASE_URL": "http://localhost:11434",
        }, clear=True), patch("core.ollama_client.ChatOllama", return_value=llm) as factory:
            client = OllamaClient()
            with self.assertRaisesRegex(RuntimeError, "MKAOS is unavailable"):
                client.chat("test")
        factory.assert_called_once_with(
            model="mkaos-local", base_url="http://127.0.0.1:11435", temperature=0.2
        )
        llm.invoke.assert_called_once()


if __name__ == "__main__":
    unittest.main()

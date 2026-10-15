import os
import unittest
from unittest.mock import patch
from core.ollama_client import OllamaClient, validate_local_ollama_url

class MkaosClientRoutingTests(unittest.TestCase):
    def test_mkaos_is_the_only_chat_provider_by_default(self):
        with patch.dict(os.environ, {}, clear=True): client = OllamaClient(model="legacy-model")
        self.assertTrue(client.mkaos_enabled)
        self.assertEqual(client.chat_base_url, "http://127.0.0.1:11435")
        self.assertEqual(client.model_name, "mkaos-local")
        self.assertEqual(client.base_url, "http://localhost:11434")

    def test_legacy_flags_cannot_switch_chat_away_from_mkaos(self):
        with patch.dict(os.environ, {"MKAOS_ENABLED":"false","MKAOS_BASE_URL":"http://127.0.0.1:11435",
            "OLLAMA_BASE_URL":"http://localhost:11434","OLLAMA_MODEL":"qwen2.5:7b"}, clear=True):
            client = OllamaClient()
        self.assertEqual(client.chat_base_url, "http://127.0.0.1:11435")
        self.assertEqual(client.model_name, "mkaos-local")

    def test_embedding_dependency_is_separate_from_chat(self):
        with patch.dict(os.environ, {"MKAOS_BASE_URL":"http://127.0.0.1:11435",
            "OLLAMA_BASE_URL":"http://localhost:11434"}, clear=True):
            client = OllamaClient()
        self.assertEqual(client.chat_base_url, "http://127.0.0.1:11435")
        self.assertEqual(client.base_url, "http://localhost:11434")

    def test_remote_mkaos_endpoint_is_rejected(self):
        with patch.dict(os.environ, {"MKAOS_BASE_URL":"https://remote.example.com"}, clear=True):
            with self.assertRaises(ValueError): OllamaClient()

    def test_chat_calls_mkaos_endpoint_only(self):
        from unittest.mock import Mock
        from langchain_core.messages import HumanMessage, SystemMessage
        llm = Mock(); llm.invoke.return_value = Mock(content="Merhaba")
        with patch.dict(os.environ, {"MKAOS_BASE_URL":"http://127.0.0.1:11435",
            "OLLAMA_BASE_URL":"http://localhost:11434"}, clear=True), patch(
            "core.ollama_client.ChatOllama", return_value=llm) as factory:
            result = OllamaClient().chat("Merhaba", system="Türkçe yanıt ver.")
        self.assertEqual(result, "Merhaba")
        self.assertEqual(factory.call_args.kwargs["base_url"], "http://127.0.0.1:11435")
        self.assertIsInstance(llm.invoke.call_args.args[0][0], SystemMessage)
        self.assertIsInstance(llm.invoke.call_args.args[0][1], HumanMessage)

    def test_mkaos_failure_never_falls_back(self):
        from unittest.mock import Mock
        llm = Mock(); llm.invoke.side_effect = RuntimeError("MKAOS is unavailable")
        with patch.dict(os.environ, {"MKAOS_BASE_URL":"http://127.0.0.1:11435",
            "OLLAMA_BASE_URL":"http://localhost:11434"}, clear=True), patch(
            "core.ollama_client.ChatOllama", return_value=llm) as factory:
            with self.assertRaisesRegex(RuntimeError, "MKAOS is unavailable"): OllamaClient().chat("test")
        self.assertEqual(factory.call_args.kwargs["base_url"], "http://127.0.0.1:11435")
        llm.invoke.assert_called_once()

    def test_remote_endpoint_validator_rejects_remote_hosts(self):
        with self.assertRaises(ValueError): validate_local_ollama_url("http://example.com:11435")

if __name__ == "__main__": unittest.main()

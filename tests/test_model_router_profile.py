import os
import unittest
from unittest.mock import patch
from core import model_router

class ModelRouterProfileTests(unittest.TestCase):
    def test_uses_small_profile_suggestions_by_default(self):
        profile = {"model_guidance": {"suggested_chat_model": "tiny-chat", "suggested_code_model": "tiny-code"}}
        with patch.dict(os.environ, {}, clear=True), patch.object(model_router, "get_runtime_profile", return_value=profile), patch.object(model_router, "OllamaClient") as client:
            model_router.ModelRouter()
        models = [call.kwargs["model"] for call in client.call_args_list]
        self.assertEqual(models, ["tiny-chat", "tiny-code", "tiny-chat"])

    def test_explicit_model_configuration_wins(self):
        profile = {"model_guidance": {"suggested_chat_model": "auto-chat", "suggested_code_model": "auto-code"}}
        env = {"OLLAMA_MODEL": "manual-default", "OLLAMA_MODEL_FAST": "manual-fast", "OLLAMA_MODEL_DEEP": "manual-deep"}
        with patch.dict(os.environ, env, clear=True), patch.object(model_router, "get_runtime_profile", return_value=profile), patch.object(model_router, "OllamaClient") as client:
            model_router.ModelRouter()
        models = [call.kwargs["model"] for call in client.call_args_list]
        self.assertEqual(models, ["manual-fast", "manual-deep", "manual-default"])

    def test_minimal_profile_has_conservative_fallback(self):
        profile = {"model_guidance": {"suggested_chat_model": None, "suggested_code_model": None}}
        with patch.dict(os.environ, {}, clear=True), patch.object(model_router, "get_runtime_profile", return_value=profile), patch.object(model_router, "OllamaClient") as client:
            model_router.ModelRouter()
        self.assertTrue(all(call.kwargs["model"] == "qwen2.5:0.5b" for call in client.call_args_list))

if __name__ == "__main__":
    unittest.main()

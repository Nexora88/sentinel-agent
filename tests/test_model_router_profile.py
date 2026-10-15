import os
import unittest
from unittest.mock import patch
from core import model_router

class ModelRouterProfileTests(unittest.TestCase):
    def test_every_task_uses_the_same_mkaos_model(self):
        with patch.dict(os.environ, {"MKAOS_BASE_URL":"http://127.0.0.1:11435",
            "OLLAMA_MODEL":"legacy-chat", "OLLAMA_MODEL_FAST":"legacy-fast",
            "OLLAMA_MODEL_DEEP":"legacy-deep"}, clear=True):
            router = model_router.ModelRouter()
        self.assertEqual(router.fast.model_name, "mkaos-local")
        self.assertEqual(router.deep.model_name, "mkaos-local")
        self.assertEqual(router.default.model_name, "mkaos-local")
        self.assertEqual(router.info()["chat_provider"], "mkaos")

    def test_task_profiles_change_sampling_not_provider(self):
        router = model_router.ModelRouter()
        self.assertEqual(router.for_task("chat").model_name, "mkaos-local")
        self.assertEqual(router.for_task("security").model_name, "mkaos-local")
        self.assertEqual(router.for_task("unknown").model_name, "mkaos-local")

if __name__ == "__main__": unittest.main()

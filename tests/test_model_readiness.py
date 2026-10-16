"""Tests for user-safe native model readiness diagnostics."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from core.model_readiness import native_model_readiness


class NativeModelReadinessTests(unittest.TestCase):
    def test_missing_model_is_actionable_and_does_not_leak_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = str(Path(tmp) / "private" / "model.mkaosw")
            result = native_model_readiness({
                "MKAOS_NATIVE_CHECKPOINT": missing,
                "MKAOS_NATIVE_SHA256": "a" * 64,
                "MKAOS_NATIVE_GENERATOR": "/missing/generator",
            })
            self.assertFalse(result["ready"])
            self.assertEqual(result["status"], "checkpoint_missing")
            self.assertNotIn(missing, str(result))

    def test_hash_mismatch_is_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model, generator = root / "model.bin", root / "generator"
            model.write_bytes(b"model")
            generator.write_bytes(b"binary")
            result = native_model_readiness({
                "MKAOS_NATIVE_CHECKPOINT": str(model),
                "MKAOS_NATIVE_SHA256": "0" * 64,
                "MKAOS_NATIVE_GENERATOR": str(generator),
            })
            self.assertEqual(result["status"], "checkpoint_hash_mismatch")

    def test_verified_local_checkpoint_is_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model, generator = root / "model.bin", root / "generator"
            model.write_bytes(b"reviewed local checkpoint")
            generator.write_bytes(b"binary")
            digest = hashlib.sha256(model.read_bytes()).hexdigest()
            result = native_model_readiness({
                "MKAOS_NATIVE_CHECKPOINT": str(model),
                "MKAOS_NATIVE_SHA256": digest,
                "MKAOS_NATIVE_GENERATOR": str(generator),
            })
            self.assertTrue(result["ready"])
            self.assertEqual(result["status"], "checkpoint_hash_verified")


if __name__ == "__main__":
    unittest.main()

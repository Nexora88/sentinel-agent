"""Unit tests for local MKAOS model bundle integrity gates."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.mkaos_model_bundle import ModelBundleError, verify_model_bundle


class ModelBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "checkpoint.bin").write_bytes(b"model-bytes")
        (self.root / "tokenizer.json").write_text('{"kind":"test"}', encoding="utf-8")
        self.manifest = {
            "schema_version": 1,
            "model_id": "mkaos-test-v1",
            "model_file": "checkpoint.bin",
            "model_sha256": hashlib.sha256(b"model-bytes").hexdigest(),
            "tokenizer_file": "tokenizer.json",
            "tokenizer_sha256": hashlib.sha256(b'{"kind":"test"}').hexdigest(),
            "tokenizer_contract": "test-tokenizer-v1",
        }
        self.path = self.root / "bundle.json"
        self.write_manifest()

    def tearDown(self):
        self.temp.cleanup()

    def write_manifest(self):
        self.path.write_text(json.dumps(self.manifest), encoding="utf-8")

    def test_valid_bundle_verifies_without_network(self):
        status = verify_model_bundle(self.path)
        self.assertEqual(status["status"], "verified")
        self.assertFalse(status["network_used"])
        self.assertFalse(status["runtime_load_tested"])

    def test_checkpoint_tampering_is_rejected(self):
        (self.root / "checkpoint.bin").write_bytes(b"tampered")
        with self.assertRaisesRegex(ModelBundleError, "SHA-256 mismatch"):
            verify_model_bundle(self.path)

    def test_tokenizer_tampering_is_rejected(self):
        (self.root / "tokenizer.json").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ModelBundleError, "SHA-256 mismatch"):
            verify_model_bundle(self.path)

    def test_path_traversal_is_rejected(self):
        self.manifest["model_file"] = "../checkpoint.bin"
        self.write_manifest()
        with self.assertRaisesRegex(ModelBundleError, "safe relative path"):
            verify_model_bundle(self.path)

    def test_missing_checkpoint_is_rejected(self):
        self.manifest["model_file"] = "missing.bin"
        self.write_manifest()
        with self.assertRaisesRegex(ModelBundleError, "does not exist"):
            verify_model_bundle(self.path)

    def test_invalid_digest_is_rejected(self):
        self.manifest["tokenizer_sha256"] = "not-a-hash"
        self.write_manifest()
        with self.assertRaisesRegex(ModelBundleError, "64-character"):
            verify_model_bundle(self.path)

    def test_unknown_schema_is_rejected(self):
        self.manifest["schema_version"] = 2
        self.write_manifest()
        with self.assertRaisesRegex(ModelBundleError, "schema_version=1"):
            verify_model_bundle(self.path)


if __name__ == "__main__":
    unittest.main()

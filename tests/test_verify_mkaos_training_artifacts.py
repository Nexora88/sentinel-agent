import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.verify_mkaos_training_artifacts import verify

MAGIC = b"MKAOSW1\0"


class VerifyMkaosArtifactsTests(unittest.TestCase):
    def write_fixture(self, root: Path):
        checkpoint = MAGIC + b"test-only-fixture"
        (root / "mkaos-owned.mkaosw").write_bytes(checkpoint)
        tokenizer_raw = (Path(__file__).resolve().parents[1] / "spec" / "mkaos-tokenizer-v1.json").read_bytes()
        (root / "tokenizer.json").write_bytes(tokenizer_raw)
        report = {
            "trained_from_random_initialization": True,
            "pretrained_model_used": None,
            "external_model_weights_used": False,
            "checkpoint_file": "mkaos-owned.mkaosw",
            "checkpoint_sha256": hashlib.sha256(checkpoint).hexdigest(),
            "tokenizer_sha256": hashlib.sha256(tokenizer_raw).hexdigest(),
            "test_used_for_training_or_model_selection": False,
        }
        path = root / "training-report.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        return path

    def test_valid_hashes_pass_with_quality_caveat(self):
        with tempfile.TemporaryDirectory() as temp:
            messages = verify(self.write_fixture(Path(temp)))
            self.assertTrue(messages[0].startswith("Artifact integrity checks passed"))
            self.assertIn("does not prove legal clearance or Turkish quality", messages[1])

    def test_tampered_checkpoint_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            report = self.write_fixture(Path(temp))
            (Path(temp) / "mkaos-owned.mkaosw").write_bytes(MAGIC + b"tampered")
            self.assertTrue(any("SHA-256 mismatch" in item for item in verify(report)))

    def test_path_traversal_checkpoint_name_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            report = self.write_fixture(Path(temp))
            payload = json.loads(report.read_text(encoding="utf-8"))
            payload["checkpoint_file"] = "../outside.mkaosw"
            report.write_text(json.dumps(payload), encoding="utf-8")
            self.assertTrue(any("filename relative" in item for item in verify(report)))


if __name__ == "__main__":
    unittest.main()

import hashlib
import json
import math
import struct
import tempfile
import unittest
from pathlib import Path

from tools.verify_mkaos_training_artifacts import verify

MAGIC = bytes([77, 75, 65, 79, 83, 87, 49, 0])


def checkpoint_bytes(name="token_embedding.weight", values=(0.25,), rows=1, cols=1, trailing=b""):
    encoded = name.encode("utf-8")
    payload = bytearray(MAGIC)
    payload.extend(struct.pack("<I", 1))
    payload.extend(struct.pack("<H", len(encoded)))
    payload.extend(encoded)
    payload.extend(struct.pack("<II", rows, cols))
    payload.extend(struct.pack("<" + "f" * len(values), *values))
    payload.extend(trailing)
    return bytes(payload)


class VerifyMkaosArtifactsTests(unittest.TestCase):
    def write_fixture(self, root: Path, checkpoint=None):
        checkpoint = checkpoint if checkpoint is not None else checkpoint_bytes()
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

    def test_valid_container_passes_with_quality_caveat(self):
        with tempfile.TemporaryDirectory() as temp:
            messages = verify(self.write_fixture(Path(temp)))
            self.assertTrue(messages[0].startswith("Artifact integrity checks passed"))
            self.assertIn("Container structure", messages[1])
            self.assertIn("does not prove legal clearance or Turkish quality", messages[2])

    def test_tampered_checkpoint_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            report = self.write_fixture(Path(temp))
            (Path(temp) / "mkaos-owned.mkaosw").write_bytes(checkpoint_bytes(values=(0.5,)))
            self.assertTrue(any("SHA-256 mismatch" in item for item in verify(report)))

    def test_path_traversal_checkpoint_name_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            report = self.write_fixture(Path(temp))
            payload = json.loads(report.read_text(encoding="utf-8"))
            payload["checkpoint_file"] = "../outside.mkaosw"
            report.write_text(json.dumps(payload), encoding="utf-8")
            self.assertTrue(any("filename relative" in item for item in verify(report)))

    def test_rejects_magic_only_or_truncated_checkpoint(self):
        with tempfile.TemporaryDirectory() as temp:
            report = self.write_fixture(Path(temp), MAGIC + bytes([0]))
            self.assertTrue(any("truncated" in item.lower() for item in verify(report)))

    def test_rejects_non_finite_weight(self):
        with tempfile.TemporaryDirectory() as temp:
            report = self.write_fixture(Path(temp), checkpoint_bytes(values=(math.nan,)))
            self.assertTrue(any("NaN or infinity" in item for item in verify(report)))

    def test_rejects_trailing_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            report = self.write_fixture(Path(temp), checkpoint_bytes(trailing=b"junk"))
            self.assertTrue(any("trailing bytes" in item for item in verify(report)))

    def test_rejects_duplicate_tensor_names(self):
        first = checkpoint_bytes()
        encoded_name = b"token_embedding.weight"
        one_tensor_length = 2 + len(encoded_name) + 8 + 4
        second_tensor = struct.pack("<H", len(encoded_name)) + encoded_name + struct.pack("<II", 1, 1) + struct.pack("<f", 0.5)
        payload = bytearray(first[:12])
        payload[:12] = MAGIC + struct.pack("<I", 2)
        payload.extend(first[12:12 + one_tensor_length])
        payload.extend(second_tensor)
        with tempfile.TemporaryDirectory() as temp:
            report = self.write_fixture(Path(temp), bytes(payload))
            self.assertTrue(any("duplicate tensor name" in item for item in verify(report)))


if __name__ == "__main__":
    unittest.main()

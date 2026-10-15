import json
import tempfile
import unittest
from pathlib import Path

from tools.train_mkaos_owned_model import encode_stream, load_governed_manifest


def record(source, split):
    return {
        "prompt": "Soru " + source, "response": "Yanıt " + source,
        "source_id": source, "source_uri": "dataset://" + source,
        "license_id": "CC-BY-4.0", "consent": True,
        "content_sha256": "hash-" + source, "split": split,
    }


class OwnedTrainingPreflightTests(unittest.TestCase):
    def test_accepts_audited_source_level_splits(self):
        manifest = {
            "training_allowed": True,
            "summary": {"content_sha256": "manifest-hash"},
            "records": [record("a", "train"), record("b", "validation"), record("c", "test")],
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            loaded, splits = load_governed_manifest(path)
        self.assertEqual(loaded["summary"]["content_sha256"], "manifest-hash")
        self.assertEqual([len(splits[key]) for key in ("train", "validation", "test")], [1, 1, 1])

    def test_refuses_unapproved_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "manifest.json"
            path.write_text(json.dumps({"training_allowed": False, "records": []}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not explicitly approved"):
                load_governed_manifest(path)

    def test_refuses_same_source_in_multiple_splits(self):
        manifest = {"training_allowed": True, "records": [
            record("same", "train"), record("same", "validation"), record("other", "test")
        ]}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source leakage"):
                load_governed_manifest(path)

    def test_utf8_byte_tokenizer_is_deterministic(self):
        self.assertEqual(encode_stream(["İstanbul", "çığöşü"]), "İstanbul\nçığöşü".encode("utf-8"))


if __name__ == "__main__":
    unittest.main()

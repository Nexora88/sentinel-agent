import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.verify_mkaos_release_artifact import verify


class ReleaseArtifactVerificationTests(unittest.TestCase):
    def test_verifies_artifact_bytes_and_reports_limits_honestly(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "mkaos.bin"
            artifact.write_bytes(b"native-build-output")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "artifact_sha256": digest,
                "source_commit": "a" * 40,
                "sbom_sha256": "b" * 64,
                "builder_id": "github-actions",
                "build_recipe": "Dockerfile@sha256:example",
            }), encoding="utf-8")

            result = verify(artifact, manifest)

            self.assertEqual(result["status"], "BYTE_IDENTITY_VERIFIED")
            self.assertEqual(result["artifact_sha256"], digest)
            self.assertEqual(result["signature_verified"], "false")
            self.assertEqual(result["license_reviewed"], "false")

    def test_rejects_artifact_digest_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "mkaos.bin"
            artifact.write_bytes(b"tampered")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "artifact_sha256": "0" * 64,
                "source_commit": "a" * 40,
                "sbom_sha256": "b" * 64,
                "builder_id": "github-actions",
                "build_recipe": "Dockerfile",
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                verify(artifact, manifest)

    def test_rejects_incomplete_provenance_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "mkaos.bin"
            artifact.write_bytes(b"output")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "artifact_sha256": hashlib.sha256(b"output").hexdigest(),
                "source_commit": "short",
                "sbom_sha256": "b" * 64,
                "builder_id": "github-actions",
                "build_recipe": "Dockerfile",
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source_commit"):
                verify(artifact, manifest)


if __name__ == "__main__":
    unittest.main()

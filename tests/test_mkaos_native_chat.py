"""Offline contract tests for the native Rust chat adapter."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from core.mkaos_native_chat import NativeMkaosUnavailable, generate_native_reply


class NativeMkaosChatTests(unittest.TestCase):
    def test_missing_checkpoint_fails_closed(self):
        with self.assertRaisesRegex(NativeMkaosUnavailable, "checkpoint is not configured"):
            generate_native_reply("Merhaba", env={})

    def test_checkpoint_and_hash_are_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / "model.mkaosw"
            binary = Path(tmp) / "mkaos-generate"
            model.write_bytes(b"checkpoint")
            binary.write_text("binary placeholder", encoding="utf-8")
            env = {"MKAOS_NATIVE_CHECKPOINT": str(model), "MKAOS_NATIVE_GENERATOR": str(binary)}
            with self.assertRaisesRegex(NativeMkaosUnavailable, "SHA-256"):
                generate_native_reply("Merhaba", env=env)

    def test_manifest_verifies_checkpoint_and_tokenizer_before_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / "model.mkaosw"
            tokenizer = root / "tokenizer.json"
            binary = root / "mkaos-generate"
            model.write_bytes(b"checkpoint")
            tokenizer.write_text('{"kind":"test"}', encoding="utf-8")
            binary.write_text("binary placeholder", encoding="utf-8")
            manifest = root / "bundle.json"
            manifest.write_text(json.dumps({
                "schema_version": 1,
                "model_id": "mkaos-test-v1",
                "model_file": model.name,
                "model_sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
                "tokenizer_file": tokenizer.name,
                "tokenizer_sha256": hashlib.sha256(tokenizer.read_bytes()).hexdigest(),
                "tokenizer_contract": "test-tokenizer-v1",
            }), encoding="utf-8")
            env = {
                "MKAOS_NATIVE_CHECKPOINT": str(model),
                "MKAOS_NATIVE_SHA256": hashlib.sha256(model.read_bytes()).hexdigest(),
                "MKAOS_NATIVE_GENERATOR": str(binary),
                "MKAOS_NATIVE_MANIFEST": str(manifest),
            }
            completed = Mock(returncode=0, stdout="Doğrulandı", stderr="")
            with patch("core.mkaos_native_chat.subprocess.run", return_value=completed) as run:
                self.assertEqual(generate_native_reply("Merhaba", env=env), "Doğrulandı")
            run.assert_called_once()

    def test_manifest_tampering_blocks_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / "model.mkaosw"
            tokenizer = root / "tokenizer.json"
            binary = root / "mkaos-generate"
            model.write_bytes(b"checkpoint")
            tokenizer.write_text('{"kind":"test"}', encoding="utf-8")
            binary.write_text("binary placeholder", encoding="utf-8")
            manifest = root / "bundle.json"
            manifest.write_text(json.dumps({
                "schema_version": 1,
                "model_id": "mkaos-test-v1",
                "model_file": model.name,
                "model_sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
                "tokenizer_file": tokenizer.name,
                "tokenizer_sha256": hashlib.sha256(tokenizer.read_bytes()).hexdigest(),
                "tokenizer_contract": "test-tokenizer-v1",
            }), encoding="utf-8")
            tokenizer.write_text("tampered", encoding="utf-8")
            env = {
                "MKAOS_NATIVE_CHECKPOINT": str(model),
                "MKAOS_NATIVE_SHA256": hashlib.sha256(model.read_bytes()).hexdigest(),
                "MKAOS_NATIVE_GENERATOR": str(binary),
                "MKAOS_NATIVE_MANIFEST": str(manifest),
            }
            with patch("core.mkaos_native_chat.subprocess.run") as run:
                with self.assertRaisesRegex(NativeMkaosUnavailable, "paketi doğrulanamadı"):
                    generate_native_reply("Merhaba", env=env)
                run.assert_not_called()

    def test_invokes_rust_cli_without_shell_and_returns_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / "model.mkaosw"
            binary = Path(tmp) / "mkaos-generate"
            model.write_bytes(b"checkpoint")
            binary.write_text("binary placeholder", encoding="utf-8")
            env = {
                "MKAOS_NATIVE_CHECKPOINT": str(model),
                "MKAOS_NATIVE_SHA256": "a" * 64,
                "MKAOS_NATIVE_GENERATOR": str(binary),
            }
            completed = Mock(returncode=0, stdout="Merhaba Türkiye\n", stderr="")
            with patch("core.mkaos_native_chat.subprocess.run", return_value=completed) as run:
                self.assertEqual(generate_native_reply("Selam", env=env), "Merhaba Türkiye")
            args, kwargs = run.call_args
            self.assertIn("--checkpoint", args[0])
            self.assertIn(str(model.resolve()), args[0])
            self.assertFalse(kwargs["shell"])
            self.assertTrue(kwargs["check"] is False)
            self.assertEqual(kwargs["timeout"], 90)

    def test_invalid_dimensions_are_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / "model.mkaosw"
            binary = Path(tmp) / "mkaos-generate"
            model.write_bytes(b"checkpoint")
            binary.write_text("binary placeholder", encoding="utf-8")
            env = {
                "MKAOS_NATIVE_CHECKPOINT": str(model),
                "MKAOS_NATIVE_SHA256": "b" * 64,
                "MKAOS_NATIVE_GENERATOR": str(binary),
                "MKAOS_NATIVE_HEADS": "3",
                "MKAOS_NATIVE_KV_HEADS": "2",
            }
            with patch("core.mkaos_native_chat.subprocess.run") as run:
                with self.assertRaisesRegex(NativeMkaosUnavailable, "divisible"):
                    generate_native_reply("Merhaba", env=env)
                run.assert_not_called()

    def test_nonzero_cli_exit_is_sanitized(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / "model.mkaosw"
            binary = Path(tmp) / "mkaos-generate"
            model.write_bytes(b"checkpoint")
            binary.write_text("binary placeholder", encoding="utf-8")
            env = {
                "MKAOS_NATIVE_CHECKPOINT": str(model),
                "MKAOS_NATIVE_SHA256": "c" * 64,
                "MKAOS_NATIVE_GENERATOR": str(binary),
            }
            completed = Mock(returncode=1, stdout="", stderr="secret filesystem detail")
            with patch("core.mkaos_native_chat.subprocess.run", return_value=completed):
                with self.assertRaises(NativeMkaosUnavailable) as caught:
                    generate_native_reply("Merhaba", env=env)
            self.assertNotIn("secret filesystem detail", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

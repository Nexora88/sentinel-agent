"""Tests for offline owned-checkpoint evaluation; inference process is mocked."""
from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "evaluate_mkaos_owned_checkpoint.py"
SPEC = importlib.util.spec_from_file_location("mkaos_owned_evaluator", SCRIPT)
assert SPEC and SPEC.loader
EVALUATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVALUATOR)


class OwnedCheckpointEvaluatorTests(unittest.TestCase):
    def test_hashes_local_checkpoint_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidate.mkaosw"
            path.write_bytes(b"local-owned-candidate")
            self.assertEqual(EVALUATOR.sha256_file(path), hashlib.sha256(b"local-owned-candidate").hexdigest())

    def test_repeated_trigram_ratio_flags_repetition(self):
        self.assertGreater(EVALUATOR.repeated_trigram_ratio("ankara istanbul izmir ankara istanbul izmir"), 0.0)
        self.assertEqual(EVALUATOR.repeated_trigram_ratio("kısa yanıt"), 0.0)

    def test_case_invokes_only_local_cli_and_records_smoke_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            generator = root / "mkaos-generate"
            checkpoint = root / "candidate.mkaosw"
            generator.write_bytes(b"placeholder executable for mocked runner")
            checkpoint.write_bytes(b"checkpoint")
            digest = EVALUATOR.sha256_file(checkpoint)
            runner = Mock(return_value=subprocess.CompletedProcess([], 0, "Ankara\n", ""))
            row = EVALUATOR.evaluate_case(
                {"id": "capital", "category": "facts", "prompt": "Türkiye'nin başkenti?", "expected_contains": ["Ankara"]},
                generator=generator, checkpoint=checkpoint, checkpoint_sha256=digest,
                heads=4, kv_heads=2, max_seq=128, max_new_tokens=16,
                timeout_seconds=10, runner=runner,
            )
            self.assertTrue(row["required_terms_pass"])
            self.assertEqual(row["answer"], "Ankara")
            args, kwargs = runner.call_args
            self.assertEqual(args[0][0], str(generator))
            self.assertIn("--checkpoint", args[0])
            self.assertIn("--sha256", args[0])
            self.assertFalse(kwargs["shell"])
            self.assertEqual(kwargs["timeout"], 10)
            self.assertNotIn("http://", " ".join(args[0]))
            self.assertNotIn("https://", " ".join(args[0]))

    def test_prompt_budget_is_checked_in_utf8_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            generator, checkpoint = root / "gen", root / "model"
            generator.write_text("x", encoding="utf-8")
            checkpoint.write_bytes(b"x")
            with self.assertRaisesRegex(ValueError, "exceeds max-seq"):
                EVALUATOR.evaluate_case(
                    {"id": "too-long", "prompt": "ğ" * 8, "expected_contains": []},
                    generator=generator, checkpoint=checkpoint, checkpoint_sha256="0" * 64,
                    heads=4, kv_heads=2, max_seq=10, max_new_tokens=3, timeout_seconds=5,
                    runner=Mock(),
                )

    def test_nonzero_cli_exit_is_a_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            generator, checkpoint = root / "gen", root / "model"
            generator.write_text("x", encoding="utf-8")
            checkpoint.write_bytes(b"x")
            with self.assertRaisesRegex(RuntimeError, "native CLI failed"):
                EVALUATOR.evaluate_case(
                    {"id": "bad", "prompt": "Merhaba", "expected_contains": []},
                    generator=generator, checkpoint=checkpoint, heads=4, kv_heads=2,
                    max_seq=128, max_new_tokens=16, timeout_seconds=5,
                    checkpoint_sha256="0" * 64,
                    runner=Mock(return_value=subprocess.CompletedProcess([], 1, "", "checkpoint rejected")),
                )


if __name__ == "__main__":
    unittest.main()

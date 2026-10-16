#!/usr/bin/env python3
"""Verify a local MKAOS training report, checkpoint SHA-256, and tokenizer contract."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAGIC = b"MKAOSW1\0"


def verify(report_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Cannot read training report: {exc}"]
    if report.get("trained_from_random_initialization") is not True:
        errors.append("Report does not assert random initialization.")
    if report.get("pretrained_model_used") is not None or report.get("external_model_weights_used") is not False:
        errors.append("Report does not establish that external pretrained weights were unused.")
    checkpoint_name = report.get("checkpoint_file")
    expected = report.get("checkpoint_sha256")
    if not isinstance(checkpoint_name, str) or Path(checkpoint_name).name != checkpoint_name:
        errors.append("checkpoint_file must be a filename relative to the report directory.")
    if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
        errors.append("checkpoint_sha256 must be lowercase 64-character hexadecimal.")
    if isinstance(checkpoint_name, str) and Path(checkpoint_name).name == checkpoint_name:
        checkpoint = report_path.parent / checkpoint_name
        try:
            raw = checkpoint.read_bytes()
        except OSError as exc:
            errors.append(f"Cannot read checkpoint: {exc}")
        else:
            actual = hashlib.sha256(raw).hexdigest()
            if not raw.startswith(MAGIC):
                errors.append("Checkpoint does not start with the MKAOSW1 format magic.")
            if isinstance(expected, str) and actual != expected:
                errors.append(f"Checkpoint SHA-256 mismatch: report={expected}, actual={actual}")
    tokenizer = report_path.parent / "tokenizer.json"
    try:
        tokenizer_raw = tokenizer.read_bytes()
        tokenizer = json.loads(tokenizer_raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"Cannot read exported tokenizer contract: {exc}")
    else:
        actual_tokenizer_hash = hashlib.sha256(tokenizer_raw).hexdigest()
        if actual_tokenizer_hash != report.get("tokenizer_sha256"):
            errors.append("Tokenizer SHA-256 does not match training report.")
        if tokenizer.get("format") != "mkaos-byte-v1" or tokenizer.get("vocab_size") != 257 or tokenizer.get("eos_id") != 256:
            errors.append("Tokenizer contract is not the supported mkaos-byte-v1/257/256 contract.")
    if report.get("test_used_for_training_or_model_selection") is not False:
        errors.append("Report must explicitly state the independent test split was not used for training/model selection.")
    return errors or [
        f"Artifact integrity checks passed: checkpoint SHA-256 {expected}.",
        "This verifies file integrity and report consistency only; it does not prove legal clearance or Turkish quality.",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Path to training-report.json")
    args = parser.parse_args()
    messages = verify(args.report)
    for message in messages:
        print(("ERROR: " if message.startswith(("Cannot ", "Report ", "checkpoint_", "Checkpoint ", "Tokenizer ", "Cannot ", "Report must")) else "INFO: ") + message)
    return 1 if any(message.startswith(("Cannot ", "Report ", "checkpoint_", "Checkpoint ", "Tokenizer ", "Report must")) for message in messages) else 0


if __name__ == "__main__":
    raise SystemExit(main())

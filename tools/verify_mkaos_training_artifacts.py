#!/usr/bin/env python3
"""Verify MKAOS report hashes and parse the checkpoint container without trusting metadata."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
from pathlib import Path

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAGIC = b"MKAOSW1\0"
MAX_TENSORS = 4096
MAX_NAME_BYTES = 256
MAX_ELEMENTS_PER_TENSOR = 100_000_000


def validate_checkpoint_container(raw: bytes) -> list[str]:
    """Validate the complete MKAOSW1 binary structure and every stored float."""
    if not raw.startswith(MAGIC):
        return ["Checkpoint does not start with the MKAOSW1 format magic."]
    if len(raw) < len(MAGIC) + 4:
        return ["Checkpoint container is truncated before tensor count."]
    offset = len(MAGIC)

    def take(size: int, label: str) -> bytes:
        nonlocal offset
        end = offset + size
        if size < 0 or end > len(raw):
            raise ValueError(f"Checkpoint container is truncated while reading {label}.")
        result = raw[offset:end]
        offset = end
        return result

    try:
        count = struct.unpack("<I", take(4, "tensor count"))[0]
        if count == 0 or count > MAX_TENSORS:
            return [f"Checkpoint tensor count is invalid: {count}."]

        names: set[str] = set()
        for index in range(count):
            name_len = struct.unpack("<H", take(2, f"tensor {index} name length"))[0]
            if name_len == 0 or name_len > MAX_NAME_BYTES:
                return [f"Checkpoint tensor {index} has an invalid name length."]
            try:
                name = take(name_len, f"tensor {index} name").decode("utf-8")
            except UnicodeDecodeError:
                return [f"Checkpoint tensor {index} name is not valid UTF-8."]
            if any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
                return [f"Checkpoint tensor {index} name contains control characters."]
            if name in names:
                return [f"Checkpoint contains duplicate tensor name: {name!r}."]
            names.add(name)

            rows, cols = struct.unpack("<II", take(8, f"tensor {name!r} dimensions"))
            if rows == 0 or cols == 0:
                return [f"Checkpoint tensor {name!r} has a zero dimension."]
            elements = rows * cols
            if elements > MAX_ELEMENTS_PER_TENSOR:
                return [f"Checkpoint tensor {name!r} exceeds the element limit."]
            payload = take(elements * 4, f"tensor {name!r} weights")
            for (value,) in struct.iter_unpack("<f", payload):
                if not math.isfinite(value):
                    return [f"Checkpoint tensor {name!r} contains NaN or infinity."]

        if offset != len(raw):
            return ["Checkpoint contains trailing bytes after the final tensor."]
    except (ValueError, struct.error) as exc:
        return [str(exc)]
    return []


def verify(report_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Cannot read training report: {exc}"]
    if not isinstance(report, dict):
        return ["Report root must be a JSON object."]
    if report.get("trained_from_random_initialization") is not True:
        errors.append("Report does not assert random initialization.")
    if report.get("pretrained_model_used") is not None or report.get("external_model_weights_used") is not False:
        errors.append("Report does not establish that external pretrained weights were unused.")

    checkpoint_name = report.get("checkpoint_file")
    expected = report.get("checkpoint_sha256")
    if not isinstance(checkpoint_name, str) or Path(checkpoint_name).name != checkpoint_name or checkpoint_name in {"", ".", ".."}:
        errors.append("checkpoint_file must be a filename relative to the report directory.")
    if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
        errors.append("checkpoint_sha256 must be lowercase 64-character hexadecimal.")
    if isinstance(checkpoint_name, str) and Path(checkpoint_name).name == checkpoint_name and checkpoint_name not in {"", ".", ".."}:
        checkpoint = report_path.parent / checkpoint_name
        try:
            raw = checkpoint.read_bytes()
        except OSError as exc:
            errors.append(f"Cannot read checkpoint: {exc}")
        else:
            actual = hashlib.sha256(raw).hexdigest()
            if not raw.startswith(MAGIC):
                errors.append("Checkpoint does not start with the MKAOSW1 format magic.")
            if isinstance(expected, str) and SHA256_RE.fullmatch(expected) and actual != expected:
                errors.append(f"Checkpoint SHA-256 mismatch: report={expected}, actual={actual}")
            errors.extend(validate_checkpoint_container(raw))

    tokenizer_path = report_path.parent / "tokenizer.json"
    try:
        tokenizer_raw = tokenizer_path.read_bytes()
        tokenizer = json.loads(tokenizer_raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"Cannot read exported tokenizer contract: {exc}")
    else:
        actual_tokenizer_hash = hashlib.sha256(tokenizer_raw).hexdigest()
        if actual_tokenizer_hash != report.get("tokenizer_sha256"):
            errors.append("Tokenizer SHA-256 does not match training report.")
        if not isinstance(tokenizer, dict) or tokenizer.get("format") != "mkaos-byte-v1" or tokenizer.get("vocab_size") != 257 or tokenizer.get("eos_id") != 256:
            errors.append("Tokenizer contract is not the supported mkaos-byte-v1/257/256 contract.")
    if report.get("test_used_for_training_or_model_selection") is not False:
        errors.append("Report must explicitly state the independent test split was not used for training/model selection.")
    return errors or [
        f"Artifact integrity checks passed: checkpoint SHA-256 {expected}.",
        "Container structure, tensor dimensions, and finite weights verified.",
        "This verifies file integrity and report consistency only; it does not prove legal clearance or Turkish quality.",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Path to training-report.json")
    args = parser.parse_args()
    messages = verify(args.report)
    for message in messages:
        print(("ERROR: " if message.startswith((
            "Cannot ", "Report ", "checkpoint_", "Checkpoint ", "Tokenizer ",
            "Checkpoint container", "Checkpoint tensor", "Checkpoint contains",
        )) else "INFO: ") + message)
    return 1 if any(message.startswith((
        "Cannot ", "Report ", "checkpoint_", "Checkpoint ", "Tokenizer ",
        "Checkpoint container", "Checkpoint tensor", "Checkpoint contains",
    )) for message in messages) else 0


if __name__ == "__main__":
    raise SystemExit(main())

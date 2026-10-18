#!/usr/bin/env python3
"""Run an audited MKAOS from-scratch training profile with exact-count checks.

This wrapper never fetches data or model weights. The underlying trainer's data
rights, source registry, split/hash and memory preflight gates remain mandatory.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.train_mkaos_from_scratch import VOCAB_SIZE, estimate_parameter_count  # noqa: E402


def load_profile(path: Path) -> dict:
    profile = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(profile, dict) or profile.get("schema_version") != 1:
        raise ValueError("profile must be a schema_version=1 JSON object")
    for section in ("model", "training"):
        if not isinstance(profile.get(section), dict):
            raise ValueError(f"profile.{section} must be an object")
    model = profile["model"]
    required_model = ("hidden_size", "layers", "heads", "kv_heads", "intermediate_size")
    if any(type(model.get(key)) is not int or model[key] < 1 for key in required_model):
        raise ValueError("profile model dimensions must be positive integers")
    actual = estimate_parameter_count(
        VOCAB_SIZE, model["hidden_size"], model["layers"], model["heads"],
        model["kv_heads"], model["intermediate_size"],
    )
    expected = profile.get("expected_parameter_count")
    if type(expected) is not int or expected != actual:
        raise ValueError(f"parameter count mismatch: profile={expected!r}, computed={actual}")
    execution_status = profile.get("execution_status", {})
    if execution_status.get("planning_only") is True or execution_status.get("blocked") is True:
        blockers = execution_status.get("blockers", [])
        detail = "; ".join(str(item) for item in blockers) or "profile is not approved for execution"
        raise ValueError(f"profile is planning-only and blocked: {detail}")
    return profile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-register", type=Path)
    parser.add_argument("--experimental-local-only", action="store_true",
                        help="Explicit opt-in for owner-supplied, non-redistributable local experiments; not legal clearance.")
    parser.add_argument("--resume-from", type=Path)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"))
    parser.add_argument("--precision", choices=("auto", "fp32", "fp16", "bf16"))
    args = parser.parse_args()

    try:
        profile = load_profile(args.profile)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))

    training = profile["training"]
    model = profile["model"]
    command = [
        sys.executable, str(ROOT / "tools" / "train_mkaos_from_scratch.py"),
        "--corpus", str(args.corpus),
        "--manifest", str(args.manifest),
        "--output-dir", str(args.output_dir),
        "--epochs", str(training["epochs"]),
        "--batch-size", str(training["batch_size"]),
        "--sequence-length", str(training["sequence_length"]),
        "--gradient-accumulation-steps", str(training["gradient_accumulation_steps"]),
        "--hidden-size", str(model["hidden_size"]),
        "--layers", str(model["layers"]),
        "--heads", str(model["heads"]),
        "--kv-heads", str(model["kv_heads"]),
        "--intermediate-size", str(model["intermediate_size"]),
        "--learning-rate", str(training["learning_rate"]),
        "--warmup-steps", str(training["warmup_steps"]),
        "--min-learning-rate-ratio", str(training["min_learning_rate_ratio"]),
        "--seed", str(training["seed"]),
        "--source-register", str(args.source_register or (ROOT / profile["governance"]["source_register"])),
    ]
    if training.get("gradient_checkpointing") is True:
        command.append("--gradient-checkpointing")
    if args.experimental_local_only:
        command.append("--experimental-local-only")
    if args.resume_from:
        command.extend(["--resume-from", str(args.resume_from)])
    if args.device:
        command.extend(["--device", args.device])
    if args.precision:
        command.extend(["--precision", args.precision])

    print(json.dumps({
        "event": "profile_validated",
        "profile_id": profile.get("profile_id"),
        "parameter_count": profile["expected_parameter_count"],
        "command": command,
        "note": "Training has not begun until the subprocess passes provenance, rights, hardware and memory gates.",
    }, ensure_ascii=False), flush=True)
    completed = subprocess.run(command, cwd=ROOT, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())


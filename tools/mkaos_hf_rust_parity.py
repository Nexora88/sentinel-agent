#!/usr/bin/env python3
"""Run the Rust SmolLM2 adapter on the exact HF reference token IDs and compare final-position logits."""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys, time
from pathlib import Path

import numpy as np

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True, help="HF .npz fixture produced by mkaos_hf_cpu_smoke.py")
    parser.add_argument("--model-dir", type=Path, required=True, help="directory with config.json and one .safetensors file")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--candidate-output", type=Path, required=True)
    parser.add_argument("--atol", type=float, default=1e-4)
    parser.add_argument("--rtol", type=float, default=1e-3)
    args = parser.parse_args()

    config_path = args.model_dir / "config.json"
    weight_files = sorted(args.model_dir.glob("*.safetensors"))
    if not config_path.is_file():
        raise SystemExit(f"config.json missing from {args.model_dir}")
    if len(weight_files) != 1:
        raise SystemExit(f"expected exactly one .safetensors file, found {len(weight_files)}")

    with np.load(args.reference, allow_pickle=False) as fixture:
        ref_all = np.asarray(fixture["logits"], dtype=np.float32)
        input_ids = np.asarray(fixture["input_ids"], dtype=np.int64).reshape(-1)
        model_id = str(fixture["model_id"].item())
        revision = str(fixture["model_revision"].item())
    if ref_all.ndim != 3 or ref_all.shape[0] != 1:
        raise SystemExit(f"unexpected reference logits shape: {ref_all.shape}")
    reference = ref_all[0, -1, :]
    if not input_ids.size:
        raise SystemExit("reference input_ids is empty")

    command = [
        "cargo", "run", "--release", "--manifest-path",
        "engine/mkaos-hf-adapter/Cargo.toml", "--bin", "mkaos_logits", "--",
        str(config_path), str(weight_files[0]), ",".join(str(int(x)) for x in input_ids),
    ]
    started = time.perf_counter()
    completed = subprocess.run(command, check=False, text=True, capture_output=True)
    elapsed = time.perf_counter() - started
    if completed.returncode != 0:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({
            "test": "hf_vs_mkaos_rust_logits_parity", "status": "BLOCKED",
            "returncode": completed.returncode, "stderr_tail": completed.stderr[-12000:],
            "conversion_status": "ADAPTER_LOAD_OR_INFERENCE_FAILED",
            "model_id": model_id, "revision": revision,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(args.report.read_text(encoding="utf-8"))
        return completed.returncode or 1
    try:
        candidate = np.asarray(json.loads(completed.stdout), dtype=np.float32).reshape(-1)
    except (json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"Rust CLI did not return a JSON float vector: {exc}; stdout={completed.stdout[:500]}") from exc
    if candidate.shape != reference.shape:
        report = {
            "test": "hf_vs_mkaos_rust_logits_parity", "status": "FAIL",
            "model_id": model_id, "revision": revision,
            "reference_logit_count": int(reference.size), "candidate_logit_count": int(candidate.size),
            "candidate_elapsed_seconds": round(elapsed, 4), "error": "vocabulary/logit length mismatch",
        }
        passed = False
        max_abs = None
        max_rel = None
        cosine = None
    else:
        diff = np.abs(reference - candidate)
        denom = np.maximum(np.abs(reference), 1e-12)
        norm = float(np.linalg.norm(reference) * np.linalg.norm(candidate))
        cosine = float(np.dot(reference, candidate) / norm) if norm else (1.0 if not np.any(reference) and not np.any(candidate) else 0.0)
        max_abs = float(np.max(diff))
        max_rel = float(np.max(diff / denom))
        passed = bool(np.allclose(reference, candidate, atol=args.atol, rtol=args.rtol))
        report = {
            "test": "hf_vs_mkaos_rust_logits_parity", "status": "PASS" if passed else "FAIL",
            "model_id": model_id, "revision": revision, "input_ids": input_ids.tolist(),
            "logit_count": int(reference.size), "max_absolute_error": max_abs,
            "max_relative_error": max_rel, "cosine_similarity": cosine,
            "atol": args.atol, "rtol": args.rtol, "passed": passed,
            "candidate_elapsed_seconds_including_cargo_build": round(elapsed, 4),
            "reference_logits_sha256": hashlib.sha256(reference.tobytes()).hexdigest(),
            "candidate_logits_sha256": hashlib.sha256(candidate.tobytes()).hexdigest(),
            "note": "Compares only final-position logits for identical token IDs. Passing this one fixture is not broad model validation.",
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.candidate_output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.candidate_output, logits=candidate, input_ids=input_ids,
                        model_id=np.asarray(model_id), model_revision=np.asarray(revision))
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())

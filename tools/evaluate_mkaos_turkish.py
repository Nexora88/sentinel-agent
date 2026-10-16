#!/usr/bin/env python3
"""Evaluate an MKAOS checkpoint through the native Rust CLI on a frozen Turkish set.

The script never trains, downloads, or modifies model weights. Lexical checks are
only a smoke-test gate; they are not a substitute for blinded human evaluation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks" / "mkaos-native-turkish-smoke-tr-001.json"
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def normalize_tr(text: str) -> str:
    """Unicode NFC + Turkish-aware lowercase without folding dotless ı into i."""
    text = unicodedata.normalize("NFC", text).replace("I", "ı").replace("İ", "i")
    return text.lower()


def load_benchmark(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("benchmark must be a schema_version=1 JSON object")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("benchmark must contain non-empty cases")
    seen: set[str] = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"case {index} must be an object")
        case_id, prompt, terms = case.get("id"), case.get("prompt"), case.get("required_terms")
        if not isinstance(case_id, str) or not case_id.strip() or case_id in seen:
            raise ValueError(f"case {index} has a missing or duplicate id")
        seen.add(case_id)
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"case {case_id} has no prompt")
        if not isinstance(terms, list) or not terms or any(not isinstance(term, str) or not term.strip() for term in terms):
            raise ValueError(f"case {case_id} needs required_terms")
    return cases


def score_output(output: str, required_terms: list[str]) -> dict[str, Any]:
    normalized = normalize_tr(output)
    matched = [term for term in required_terms if normalize_tr(term) in normalized]
    return {"passed": len(matched) == len(required_terms), "matched_terms": matched,
            "missing_terms": [term for term in required_terms if term not in matched]}


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    if not SHA256_RE.fullmatch(args.sha256):
        raise ValueError("--sha256 must be a 64-character hexadecimal digest")
    cases = load_benchmark(args.benchmark)
    checkpoint = args.checkpoint.resolve()
    if not checkpoint.is_file():
        raise ValueError("checkpoint file does not exist")
    digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    if digest.lower() != args.sha256.lower():
        raise ValueError("checkpoint SHA-256 does not match --sha256")
    binary = args.binary.resolve()
    if not binary.is_file():
        raise ValueError("Rust inference binary does not exist")

    results: list[dict[str, Any]] = []
    for case in cases:
        command = [
            str(binary), "--checkpoint", str(checkpoint), "--sha256", digest,
            "--heads", str(args.heads), "--kv-heads", str(args.kv_heads),
            "--max-seq", str(args.max_seq), "--max-new-tokens", str(args.max_new_tokens),
            "--prompt", case["prompt"],
        ]
        started = time.perf_counter()
        try:
            completed = subprocess.run(command, check=False, capture_output=True, text=True,
                                       timeout=args.timeout_seconds, shell=False)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        except subprocess.TimeoutExpired:
            results.append({"id": case["id"], "passed": False, "error": "timeout",
                            "latency_ms": round((time.perf_counter() - started) * 1000, 2)})
            continue
        if completed.returncode != 0:
            results.append({"id": case["id"], "passed": False, "error": "rust_inference_failed",
                            "stderr": completed.stderr[-1000:], "latency_ms": elapsed_ms})
            continue
        output = completed.stdout.strip()
        score = score_output(output, case["required_terms"])
        results.append({"id": case["id"], "prompt": case["prompt"], "output": output,
                        **score, "latency_ms": elapsed_ms})

    passed = sum(1 for item in results if item.get("passed") is True)
    total = len(results)
    report = {
        "schema_version": 1,
        "model_id": args.model_id,
        "checkpoint_sha256": digest,
        "benchmark": str(args.benchmark.name),
        "benchmark_cases": total,
        "passed_cases": passed,
        "smoke_pass_rate": round(passed / total, 4) if total else 0.0,
        "threshold": args.minimum_pass_rate,
        "smoke_gate_passed": (passed / total >= args.minimum_pass_rate) if total else False,
        "human_reviewed": False,
        "release_eligible": False,
        "limitations": [
            "Required-term checks are a smoke test, not a measure of general reasoning or factuality.",
            "Human-blinded Turkish quality, privacy/memorization, and safety review remain mandatory.",
            "Passing this script does not establish legal clearance or competitive model quality."
        ],
        "results": results,
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True, help="built mkaos-generate binary")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--model-id", default="mkaos-turkish-from-scratch-experimental")
    parser.add_argument("--heads", type=int, required=True)
    parser.add_argument("--kv-heads", type=int, required=True)
    parser.add_argument("--max-seq", type=int, default=512)
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--timeout-seconds", type=float, default=60)
    parser.add_argument("--minimum-pass-rate", type=float, default=0.5)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    if args.heads < 1 or args.kv_heads < 1 or args.max_seq < 1 or args.max_new_tokens < 1:
        parser.error("model dimensions and token limits must be positive")
    if args.timeout_seconds <= 0 or not 0 <= args.minimum_pass_rate <= 1:
        parser.error("timeout must be positive and minimum pass rate must be in [0, 1]")
    try:
        report = evaluate(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Turkish model evaluation blocked: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        try:
            with args.report.open("x", encoding="utf-8") as handle:
                handle.write(rendered)
        except FileExistsError:
            print(f"Refusing to overwrite report: {args.report}", file=sys.stderr)
            return 2
    print(rendered, end="")
    return 0 if report["smoke_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

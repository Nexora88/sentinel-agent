#!/usr/bin/env python3
"""Evaluate a locally trained MKAOSW1 checkpoint through the native Rust CLI.

This evaluator is intentionally offline: it never downloads models or calls HTTP.
It measures repeatable smoke metrics, not semantic correctness or model ownership.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repeated_trigram_ratio(text: str) -> float:
    tokens = re.findall(r"[^\W_]+|[^\w\s]", text.casefold(), flags=re.UNICODE)
    if len(tokens) < 3:
        return 0.0
    grams = [tuple(tokens[i:i + 3]) for i in range(len(tokens) - 2)]
    return 1.0 - len(set(grams)) / len(grams)


def evaluate_case(
    case: dict[str, Any],
    *,
    generator: Path,
    checkpoint: Path,
    checkpoint_sha256: str,
    heads: int,
    kv_heads: int,
    max_seq: int,
    max_new_tokens: int,
    timeout_seconds: int,
    runner: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    prompt = case.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError(f"{case.get('id', '<unknown>')}: prompt must be a non-empty string")
    if len(prompt.encode("utf-8")) + max_new_tokens > max_seq:
        raise ValueError(
            f"{case.get('id', '<unknown>')}: UTF-8 prompt bytes + max-new-tokens exceeds max-seq"
        )

    command = [
        str(generator), "--checkpoint", str(checkpoint), "--sha256", checkpoint_sha256,
        "--heads", str(heads), "--kv-heads", str(kv_heads),
        "--max-seq", str(max_seq), "--max-new-tokens", str(max_new_tokens),
        "--prompt", prompt,
    ]
    execute = runner or subprocess.run
    started = time.perf_counter()
    completed = execute(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout_seconds, shell=False, close_fds=True,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    if completed.returncode != 0:
        stderr = str(getattr(completed, "stderr", ""))[-1000:]
        raise RuntimeError(f"{case.get('id', '<unknown>')}: native CLI failed: {stderr}")
    answer = str(getattr(completed, "stdout", "")).strip()
    if not answer:
        raise RuntimeError(f"{case.get('id', '<unknown>')}: native CLI returned an empty answer")

    folded = answer.casefold()
    required = case.get("expected_contains", [])
    any_required = case.get("any_expected_contains", [])
    if not isinstance(required, list) or not all(isinstance(x, str) for x in required):
        raise ValueError(f"{case.get('id', '<unknown>')}: expected_contains must be a string array")
    if not isinstance(any_required, list) or not all(isinstance(x, str) for x in any_required):
        raise ValueError(f"{case.get('id', '<unknown>')}: any_expected_contains must be a string array")
    missing = [term for term in required if term.casefold() not in folded]
    all_ok = not missing
    any_ok = not any_required or any(term.casefold() in folded for term in any_required)
    return {
        "id": case.get("id", "unnamed"),
        "category": case.get("category", "uncategorized"),
        "answer": answer,
        "required_terms_pass": all_ok and any_ok,
        "missing_required_terms": missing,
        "any_term_group_pass": any_ok,
        "repeated_trigram_ratio": round(repeated_trigram_ratio(answer), 4),
        "wall_time_ms": round(elapsed_ms, 2),
        "generated_tokens_per_second": None,
        "metrics_note": "CLI emits text only; token count and tokens/s are not available without changing the runtime protocol.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generator", required=True, type=Path, help="already-built local mkaos-generate binary")
    parser.add_argument("--checkpoint", required=True, type=Path, help="local MKAOSW1 checkpoint")
    parser.add_argument("--expected-sha256", help="optional reviewed digest; mismatch fails before inference")
    parser.add_argument("--dataset", type=Path, default=Path("benchmarks/mkaos-quality-tr-001.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/mkaos-owned-quality-report.json"))
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--kv-heads", type=int, default=2)
    parser.add_argument("--max-seq", type=int, default=2048)
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    args = parser.parse_args(argv)

    if not args.generator.is_file():
        parser.error("--generator must point to an existing local executable")
    if not args.checkpoint.is_file():
        parser.error("--checkpoint must point to an existing local checkpoint")
    if args.heads < 1 or args.kv_heads < 1 or args.heads % args.kv_heads:
        parser.error("--heads and --kv-heads must be positive and heads must divide by kv-heads")
    if args.max_seq < 2 or args.max_new_tokens < 1 or args.max_new_tokens >= args.max_seq:
        parser.error("invalid sequence/token budget")
    if not 1 <= args.timeout_seconds <= 3600:
        parser.error("--timeout-seconds must be in 1..3600")

    checkpoint_hash = sha256_file(args.checkpoint)
    if args.expected_sha256 and checkpoint_hash != args.expected_sha256.lower():
        print("ERROR: local checkpoint SHA-256 does not match --expected-sha256", file=sys.stderr)
        return 2
    try:
        dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
        cases = dataset.get("cases") if isinstance(dataset, dict) else None
        if not isinstance(cases, list) or not cases:
            raise ValueError("dataset must contain a non-empty cases array")
        rows = [
            evaluate_case(
                case, generator=args.generator.resolve(), checkpoint=args.checkpoint.resolve(),
                checkpoint_sha256=checkpoint_hash, heads=args.heads, kv_heads=args.kv_heads,
                max_seq=args.max_seq, max_new_tokens=args.max_new_tokens,
                timeout_seconds=args.timeout_seconds,
            )
            for case in cases
        ]
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: evaluation stopped safely: {exc}", file=sys.stderr)
        return 2

    categories: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        categories.setdefault(row["category"], []).append(row)
    by_category = {
        name: {
            "cases": len(items),
            "required_terms_pass_rate": sum(row["required_terms_pass"] for row in items) / len(items),
            "mean_repeated_trigram_ratio": round(statistics.mean(row["repeated_trigram_ratio"] for row in items), 4),
            "mean_wall_time_ms": round(statistics.mean(row["wall_time_ms"] for row in items), 2),
        }
        for name, items in sorted(categories.items())
    }
    report = {
        "schema_version": 1,
        "dataset_id": dataset.get("dataset_id", args.dataset.stem),
        "mode": "native-owned-checkpoint-candidate",
        "checkpoint_path_basename": args.checkpoint.name,
        "checkpoint_sha256": checkpoint_hash,
        "checkpoint_provenance": "not verified by this evaluator; consult the reviewed source and training records",
        "generator_path_basename": args.generator.name,
        "heads": args.heads,
        "kv_heads": args.kv_heads,
        "max_seq": args.max_seq,
        "max_new_tokens": args.max_new_tokens,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "case_count": len(rows),
        "required_terms_pass_rate": sum(row["required_terms_pass"] for row in rows) / len(rows),
        "mean_repeated_trigram_ratio": round(statistics.mean(row["repeated_trigram_ratio"] for row in rows), 4),
        "mean_wall_time_ms": round(statistics.mean(row["wall_time_ms"] for row in rows), 2),
        "by_category": by_category,
        "results": rows,
        "limitations": [
            "Substring checks are a small smoke metric, not semantic correctness, reasoning quality, or expert grading.",
            "The evaluator cannot prove that a checkpoint was trained from scratch or that its data and license are cleared.",
            "Wall time includes process startup and checkpoint loading for each case; repeat runs on target hardware.",
            "The current CLI emits text only, so token throughput and time-to-first-token are not measured.",
            "Keep reports with private/custom prompts local; the report includes generated answers and test case identifiers.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "dataset_id": report["dataset_id"],
        "checkpoint_sha256": checkpoint_hash,
        "case_count": len(rows),
        "required_terms_pass_rate": report["required_terms_pass_rate"],
        "mean_repeated_trigram_ratio": report["mean_repeated_trigram_ratio"],
        "mean_wall_time_ms": report["mean_wall_time_ms"],
        "by_category": by_category,
    }, ensure_ascii=False, indent=2))
    print(f"Full report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

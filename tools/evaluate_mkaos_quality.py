#!/usr/bin/env python3
"""Run the fixed MKAOS quality set against a downloaded local model and report regressions."""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path


def repeated_trigram_ratio(text: str) -> float:
    tokens = re.findall(r"[^\W_]+|[^\w\s]", text.casefold(), flags=re.UNICODE)
    if len(tokens) < 3:
        return 0.0
    grams = [tuple(tokens[i:i + 3]) for i in range(len(tokens) - 2)]
    return 1.0 - (len(set(grams)) / len(grams))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--dataset", default="benchmarks/mkaos-quality-tr-001.json")
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--repetition-penalty", type=float, default=1.10)
    parser.add_argument("--output", default="artifacts/mkaos-quality-report.json")
    args = parser.parse_args()
    if args.max_new_tokens < 1 or args.max_new_tokens > 512:
        parser.error("--max-new-tokens must be between 1 and 512")
    if not 1.0 <= args.repetition_penalty <= 2.0:
        parser.error("--repetition-penalty must be between 1.0 and 2.0")

    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    env = os.environ.copy()
    env["MKAOS_REPETITION_PENALTY"] = str(args.repetition_penalty)
    rows = []
    for case in dataset["cases"]:
        command = [
            "cargo", "run", "--release", "--quiet",
            "--manifest-path", "engine/mkaos-hf-adapter/Cargo.toml",
            "--bin", "mkaos_generate", "--", args.model_dir,
            case["prompt"], str(args.max_new_tokens),
        ]
        started = time.perf_counter()
        result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=900)
        elapsed_ms = (time.perf_counter() - started) * 1000
        if result.returncode:
            print(f"ERROR {case['id']}: {result.stderr[-1500:]}", file=sys.stderr)
            return result.returncode
        try:
            output = json.loads(result.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            print(f"ERROR {case['id']}: CLI did not return JSON", file=sys.stderr)
            return 2

        answer = str(output.get("text", "")).strip()
        folded = answer.casefold()
        required = case.get("expected_contains", [])
        all_required = all(value.casefold() in folded for value in required)
        any_required = case.get("any_expected_contains", [])
        any_ok = not any_required or any(value.casefold() in folded for value in any_required)
        ratio = repeated_trigram_ratio(answer)
        rows.append({
            "id": case["id"], "category": case["category"], "prompt": case["prompt"],
            "answer": answer, "required_terms_pass": all_required and any_ok,
            "missing_required_terms": [value for value in required if value.casefold() not in folded],
            "any_term_group_pass": any_ok, "repeated_trigram_ratio": round(ratio, 4),
            "prompt_tokens": output.get("prompt_token_count"),
            "generated_tokens": output.get("generated_token_count"),
            "model_load_ms": output.get("model_load_ms"),
            "prefill_ms": output.get("prefill_ms"),
            "first_token_ms": output.get("first_token_ms"),
            "tokens_per_second": output.get("tokens_per_second"),
            "wall_time_ms_including_process_and_load": round(elapsed_ms, 2),
        })

    by_category = {}
    for category in sorted({row["category"] for row in rows}):
        subset = [row for row in rows if row["category"] == category]
        by_category[category] = {
            "cases": len(subset),
            "required_terms_pass_rate": sum(row["required_terms_pass"] for row in subset) / len(subset),
            "mean_repeated_trigram_ratio": statistics.mean(row["repeated_trigram_ratio"] for row in subset),
        }
    report = {
        "schema_version": 1, "dataset_id": dataset["dataset_id"],
        "model_dir": args.model_dir, "repetition_penalty": args.repetition_penalty,
        "case_count": len(rows),
        "required_terms_pass_rate": sum(row["required_terms_pass"] for row in rows) / len(rows),
        "mean_first_token_ms": statistics.mean(row["first_token_ms"] for row in rows if row["first_token_ms"] is not None),
        "mean_tokens_per_second": statistics.mean(row["tokens_per_second"] for row in rows if row["tokens_per_second"] is not None),
        "mean_model_load_ms": statistics.mean(row["model_load_ms"] for row in rows if row["model_load_ms"] is not None),
        "by_category": by_category, "results": rows,
        "limitations": [
            "Substring checks are a smoke-test metric, not semantic correctness or expert grading.",
            "Each CLI invocation loads the model again; wall time therefore includes process startup and model loading.",
            "Run multiple times on the target device before making latency or quality claims."
        ]
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "dataset_id", "case_count", "required_terms_pass_rate", "mean_first_token_ms",
        "mean_tokens_per_second", "mean_model_load_ms", "by_category"
    )}, ensure_ascii=False, indent=2))
    print(f"Full report: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

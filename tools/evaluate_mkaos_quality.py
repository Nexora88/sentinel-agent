#!/usr/bin/env python3
"""Evaluate fixed MKAOS quality cases through either the CLI or resident HTTP server."""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def repeated_trigram_ratio(text: str) -> float:
    tokens = re.findall(r"[^\W_]+|[^\w\s]", text.casefold(), flags=re.UNICODE)
    if len(tokens) < 3:
        return 0.0
    grams = [tuple(tokens[i:i + 3]) for i in range(len(tokens) - 2)]
    return 1.0 - (len(set(grams)) / len(grams))


def mean_or_none(values: list[float]) -> float | None:
    return round(statistics.mean(values), 2) if values else None


def run_cli_case(case: dict, args: argparse.Namespace, env: dict) -> tuple[dict, float]:
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
        raise RuntimeError(f"{case['id']}: {result.stderr[-1500:]}")
    try:
        output = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        raise RuntimeError(f"{case['id']}: CLI did not return metrics JSON") from exc
    return output, elapsed_ms


def run_server_case(case: dict, args: argparse.Namespace) -> tuple[dict, float]:
    payload = json.dumps({
        "model": "mkaos-local",
        "prompt": case["prompt"],
        "options": {
            "num_predict": args.max_new_tokens,
            "temperature": 0.0,
            "top_p": 0.9,
            "repeat_penalty": args.repetition_penalty,
        },
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        args.server_url.rstrip("/") + "/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            records = [line for line in response.read().splitlines() if line.strip()]
    except Exception as exc:
        raise RuntimeError(f"{case['id']}: resident server request failed: {exc}") from exc
    elapsed_ms = (time.perf_counter() - started) * 1000
    if not records:
        raise RuntimeError(f"{case['id']}: resident server returned an empty response")
    try:
        raw = json.loads(records[-1])
    except ValueError as exc:
        raise RuntimeError(f"{case['id']}: resident server returned invalid JSON") from exc
    eval_ns = int(raw.get("eval_duration", 0) or 0)
    eval_count = int(raw.get("eval_count", 0) or 0)
    output = {
        "text": raw.get("response", ""),
        "prompt_token_count": raw.get("prompt_eval_count"),
        "generated_token_count": eval_count,
        "model_load_ms": int(raw.get("load_duration", 0) or 0) / 1e6,
        "prefill_ms": int(raw.get("prompt_eval_duration", 0) or 0) / 1e6,
        "first_token_ms": None,
        "tokens_per_second": eval_count / (eval_ns / 1e9) if eval_ns > 0 else None,
        "prefix_cache_hit": raw.get("mkaos_prefix_cache_hit"),
    }
    return output, elapsed_ms


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", help="downloaded model directory for CLI evaluation")
    parser.add_argument("--server-url", help="resident MKAOS base URL, e.g. http://127.0.0.1:11435")
    parser.add_argument("--dataset", default="benchmarks/mkaos-quality-tr-001.json")
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--repetition-penalty", type=float, default=1.10)
    parser.add_argument("--output", default="artifacts/mkaos-quality-report.json")
    args = parser.parse_args()
    if not args.server_url and not args.model_dir:
        parser.error("provide either --model-dir or --server-url")
    if args.max_new_tokens < 1 or args.max_new_tokens > 512:
        parser.error("--max-new-tokens must be between 1 and 512")
    if not 1.0 <= args.repetition_penalty <= 2.0:
        parser.error("--repetition-penalty must be between 1.0 and 2.0")

    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    env = os.environ.copy()
    env["MKAOS_REPETITION_PENALTY"] = str(args.repetition_penalty)
    rows = []
    for case in dataset["cases"]:
        try:
            output, elapsed_ms = (
                run_server_case(case, args) if args.server_url else run_cli_case(case, args, env)
            )
        except RuntimeError as exc:
            print(f"ERROR {exc}", file=sys.stderr)
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
            "prefix_cache_hit": output.get("prefix_cache_hit"),
            "wall_time_ms_including_process_and_request": round(elapsed_ms, 2),
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
        "mode": "resident_server" if args.server_url else "cli",
        "model_dir": args.model_dir, "server_url": args.server_url,
        "repetition_penalty": args.repetition_penalty,
        "case_count": len(rows),
        "required_terms_pass_rate": sum(row["required_terms_pass"] for row in rows) / len(rows),
        "mean_first_token_ms": mean_or_none([row["first_token_ms"] for row in rows if row["first_token_ms"] is not None]),
        "mean_tokens_per_second": mean_or_none([row["tokens_per_second"] for row in rows if row["tokens_per_second"] is not None]),
        "mean_model_load_ms_per_request": mean_or_none([row["model_load_ms"] for row in rows if row["model_load_ms"] is not None]),
        "mean_wall_time_ms": mean_or_none([row["wall_time_ms_including_process_and_request"] for row in rows]),
        "prefix_cache_hit_count": sum(row["prefix_cache_hit"] is True for row in rows),
        "prefix_cache_hit_rate": sum(row["prefix_cache_hit"] is True for row in rows) / len(rows) if args.server_url else None,
        "by_category": by_category, "results": rows,
        "limitations": [
            "Substring checks are a smoke-test metric, not semantic correctness or expert grading.",
            "CLI mode loads the model on each invocation; resident-server mode measures requests after the server is already started.",
            "The resident API currently returns one response record after generation, so it does not expose token-by-token first-token latency.",
            "Run multiple times on the target device before making latency or quality claims."
        ]
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "dataset_id", "mode", "case_count", "required_terms_pass_rate", "mean_first_token_ms",
        "mean_tokens_per_second", "mean_model_load_ms_per_request", "mean_wall_time_ms", "prefix_cache_hit_count", "prefix_cache_hit_rate", "by_category"
    )}, ensure_ascii=False, indent=2))
    print(f"Full report: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

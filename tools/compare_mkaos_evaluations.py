#!/usr/bin/env python3
"""Compare two MKAOS fixed-test evaluation reports without blending away task failures."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def _finite_number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and math.isfinite(value) else None


def compare(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    if baseline.get("dataset_id") != candidate.get("dataset_id"):
        raise ValueError("reports use different dataset_id values")
    base_hash, new_hash = baseline.get("dataset_sha256"), candidate.get("dataset_sha256")
    if not isinstance(base_hash, str) or not base_hash or base_hash != new_hash:
        raise ValueError("reports must contain the same non-empty dataset_sha256; regenerate both on the exact same dataset file")
    base_cases = {row.get("case_id"): row for row in baseline.get("cases", []) if isinstance(row, dict)}
    new_cases = {row.get("case_id"): row for row in candidate.get("cases", []) if isinstance(row, dict)}
    if not base_cases or set(base_cases) != set(new_cases):
        raise ValueError("reports must include the same non-empty set of case IDs")
    categories = sorted({str(row.get("category", "uncategorized")) for row in base_cases.values()})
    category_results = {}
    for category in categories:
        b_rows = [r for r in base_cases.values() if str(r.get("category", "uncategorized")) == category]
        n_rows = [new_cases[r["case_id"]] for r in b_rows]
        b_score = sum(bool(r.get("passed_heuristic")) for r in b_rows) / len(b_rows)
        n_score = sum(bool(r.get("passed_heuristic")) for r in n_rows) / len(n_rows)
        category_results[category] = {
            "baseline_accuracy": b_score,
            "candidate_accuracy": n_score,
            "delta": n_score - b_score,
            "regressed_case_ids": [b["case_id"] for b, n in zip(b_rows, n_rows) if b.get("passed_heuristic") and not n.get("passed_heuristic")],
            "improved_case_ids": [b["case_id"] for b, n in zip(b_rows, n_rows) if not b.get("passed_heuristic") and n.get("passed_heuristic")],
        }

    def delta(path: tuple[str, ...]) -> dict[str, float | None]:
        def value(report: dict[str, Any]) -> float | None:
            item: Any = report
            for key in path:
                item = item.get(key) if isinstance(item, dict) else None
            return _finite_number(item)
        b, n = value(baseline), value(candidate)
        return {"baseline": b, "candidate": n, "delta_candidate_minus_baseline": n - b if b is not None and n is not None else None}

    base_accuracy = _finite_number(baseline.get("overall_heuristic_accuracy"))
    new_accuracy = _finite_number(candidate.get("overall_heuristic_accuracy"))
    base_rep = _finite_number(baseline.get("repetition", {}).get("mean_repeated_4gram_ratio"))
    new_rep = _finite_number(candidate.get("repetition", {}).get("mean_repeated_4gram_ratio"))
    regressions = [case_id for case_id in sorted(base_cases) if base_cases[case_id].get("passed_heuristic") and not new_cases[case_id].get("passed_heuristic")]
    improvements = [case_id for case_id in sorted(base_cases) if not base_cases[case_id].get("passed_heuristic") and new_cases[case_id].get("passed_heuristic")]
    return {
        "schema_version": 1,
        "dataset_id": baseline["dataset_id"],
        "dataset_sha256": base_hash,
        "cases_compared": len(base_cases),
        "overall": {
            "baseline_heuristic_accuracy": base_accuracy,
            "candidate_heuristic_accuracy": new_accuracy,
            "heuristic_accuracy_delta": new_accuracy - base_accuracy if base_accuracy is not None and new_accuracy is not None else None,
            "baseline_mean_repeated_4gram_ratio": base_rep,
            "candidate_mean_repeated_4gram_ratio": new_rep,
            "repetition_delta_candidate_minus_baseline": new_rep - base_rep if base_rep is not None and new_rep is not None else None,
            "median_latency_ms": delta(("latency_ms", "median")),
            "p95_latency_ms": delta(("latency_ms", "p95")),
            "max_peak_memory_mb": delta(("peak_memory_mb", "max")),
        },
        "by_category": category_results,
        "regressed_case_ids": regressions,
        "improved_case_ids": improvements,
        "limitations": [
            "Expected-term accuracy is a deterministic lexical smoke metric, not a factuality or reasoning judge.",
            "Human review is required for instruction compliance, factual claims, citations, uncertainty and Turkish quality.",
            "Latency and memory comparisons are meaningful only when hardware, build, decoding settings, and measurement method match.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
        result = compare(baseline, candidate)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({"dataset_id": result["dataset_id"], "cases_compared": result["cases_compared"], "regressed_case_ids": result["regressed_case_ids"], "report": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

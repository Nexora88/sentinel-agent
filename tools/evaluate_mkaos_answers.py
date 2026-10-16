#!/usr/bin/env python3
"""Score MKAOS answers against the fixed Turkish regression set.

This is a deterministic lexical/format smoke scorer, not a judge of truth or
reasoning. Human review remains required for factuality, citations and nuance.
Input JSONL rows: {"case_id": "...", "answer": "...", optional "latency_ms": 12.3,
optional "peak_memory_mb": 512}.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold().replace("\u0307", "")


def read_answers(path: Path) -> dict[str, dict[str, Any]]:
    answers: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict) or not isinstance(row.get("case_id"), str):
                raise ValueError(f"{path}:{line_number}: case_id must be a string")
            if not isinstance(row.get("answer"), str):
                raise ValueError(f"{path}:{line_number}: answer must be a string")
            case_id = row["case_id"]
            if case_id in answers:
                raise ValueError(f"{path}:{line_number}: duplicate answer for {case_id!r}")
            for key in ("latency_ms", "peak_memory_mb"):
                if key in row and (type(row[key]) not in (int, float) or not math.isfinite(row[key]) or row[key] < 0):
                    raise ValueError(f"{path}:{line_number}: {key} must be a finite non-negative number")
            answers[case_id] = row
    return answers


def repetition_ratio(text: str, n: int = 4) -> float:
    """Fraction of word n-grams that repeat after their first occurrence."""
    words = normalize(text).split()
    if len(words) < n:
        return 0.0
    grams = [tuple(words[i:i+n]) for i in range(len(words) - n + 1)]
    counts = Counter(grams)
    repeated = sum(count - 1 for count in counts.values() if count > 1)
    return repeated / len(grams)


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))
    return float(ordered[index])


def evaluate(dataset: dict[str, Any], answers: dict[str, dict[str, Any]]) -> dict[str, Any]:
    cases = dataset.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("dataset must contain a non-empty cases array")
    case_ids = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(case_ids) != len(cases) or any(not isinstance(case_id, str) for case_id in case_ids):
        raise ValueError("every test case must have a string id")
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("dataset contains duplicate case IDs")
    unexpected = sorted(set(answers) - set(case_ids))

    detail = []
    category_totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    latencies: list[float] = []
    memory: list[float] = []
    repetitions: list[float] = []
    for case in cases:
        case_id = case["id"]
        category = str(case.get("category", "uncategorized"))
        row = answers.get(case_id, {"answer": ""})
        answer = row["answer"]
        normalized_answer = normalize(answer)
        expected = case.get("expected_contains", [])
        alternatives = case.get("any_expected_contains", [])
        required_ok = all(normalize(str(term)) in normalized_answer for term in expected)
        alternatives_ok = not alternatives or any(normalize(str(term)) in normalized_answer for term in alternatives)
        passed = bool(answer.strip()) and required_ok and alternatives_ok
        category_totals[category][1] += 1
        category_totals[category][0] += int(passed)
        repeat = repetition_ratio(answer)
        repetitions.append(repeat)
        if isinstance(row.get("latency_ms"), (int, float)):
            latencies.append(float(row["latency_ms"]))
        if isinstance(row.get("peak_memory_mb"), (int, float)):
            memory.append(float(row["peak_memory_mb"]))
        detail.append({
            "case_id": case_id, "category": category, "passed_heuristic": passed,
            "missing_required_terms": [term for term in expected if normalize(str(term)) not in normalized_answer],
            "missing_alternative_group": bool(alternatives and not alternatives_ok),
            "answer_present": bool(answer.strip()), "repetition_ratio": round(repeat, 6),
            "latency_ms": row.get("latency_ms"), "peak_memory_mb": row.get("peak_memory_mb"),
        })

    return {
        "schema_version": 1,
        "dataset_id": dataset.get("dataset_id"),
        "scoring_note": "Lexical/format smoke score only. It does not prove factual correctness, semantic understanding, citation support, or safe reasoning. Human review required.",
        "cases_total": len(cases),
        "answers_received": len(answers),
        "missing_answer_ids": sorted(set(case_ids) - set(answers)),
        "unexpected_answer_ids": unexpected,
        "overall_heuristic_accuracy": sum(x["passed_heuristic"] for x in detail) / len(detail),
        "by_category": {
            category: {"passed": counts[0], "total": counts[1], "accuracy": counts[0] / counts[1]}
            for category, counts in sorted(category_totals.items())
        },
        "repetition": {
            "mean_repeated_4gram_ratio": statistics.mean(repetitions) if repetitions else 0.0,
            "answers_with_repeated_4grams": sum(x > 0 for x in repetitions),
        },
        "latency_ms": {
            "samples": len(latencies),
            "median": statistics.median(latencies) if latencies else None,
            "p95": percentile(latencies, 0.95),
        },
        "peak_memory_mb": {"samples": len(memory), "max": max(memory) if memory else None},
        "cases": detail,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("benchmarks/mkaos-general-llm-tr-001.json"))
    parser.add_argument("--answers", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
        answers = read_answers(args.answers)
        report = evaluate(dataset, answers)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({
        "dataset_id": report["dataset_id"],
        "cases_total": report["cases_total"],
        "answers_received": report["answers_received"],
        "overall_heuristic_accuracy": report["overall_heuristic_accuracy"],
        "report": str(args.output),
        "human_review_required": True,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

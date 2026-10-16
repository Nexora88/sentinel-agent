#!/usr/bin/env python3
"""Score an independently curated Turkish task benchmark without changing the model.

Input JSONL stays local and must contain reviewed, permitted test cases. The
prediction must come from the exact Rust-loaded checkpoint under evaluation.
This script never trains, selects checkpoints, or uploads prompt/answer text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

REQUIRED = ("case_id", "task", "prompt", "reference", "prediction",
            "source_id", "document_group", "human_review", "split")
ALLOWED_TASKS = {"instruction_following", "reading_comprehension", "summarization",
                 "grammar", "factuality", "safety", "general_knowledge"}


def norm(value: str) -> str:
    # Preserve Turkish dotted/dotless-I distinctions; casefold alone is deliberate.
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"\w+", value, flags=re.UNICODE))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def evaluate(rows: list[dict[str, Any]], *, checkpoint_sha256: str) -> dict[str, Any]:
    errors: list[str] = []
    seen: set[str] = set()
    source_splits: dict[str, set[str]] = defaultdict(set)
    group_splits: dict[str, set[str]] = defaultdict(set)
    per_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    exact = nonempty = 0
    human_scores: list[int] = []
    output_hashes: list[str] = []
    for i, row in enumerate(rows, 1):
        missing = [key for key in REQUIRED if not isinstance(row.get(key), str) or not row[key].strip()]
        if missing:
            errors.append(f"row {i}: missing fields {','.join(missing)}")
            continue
        if row["case_id"] in seen:
            errors.append(f"row {i}: duplicate case_id")
        seen.add(row["case_id"])
        if row["split"] != "test":
            errors.append(f"row {i}: independent evaluation accepts test rows only")
        if row["human_review"] != "approved":
            errors.append(f"row {i}: human_review must be approved")
        if row["task"] not in ALLOWED_TASKS:
            errors.append(f"row {i}: unsupported task category")
        if not row["prediction"].strip():
            errors.append(f"row {i}: empty prediction")
        source_splits[row["source_id"]].add(row["split"])
        group_splits[row["document_group"]].add(row["split"])
        ref, pred = norm(row["reference"]), norm(row["prediction"])
        is_exact = bool(ref) and ref == pred
        exact += int(is_exact)
        nonempty += int(bool(pred))
        item: dict[str, Any] = {"exact_match": is_exact, "prediction_nonempty": bool(pred)}
        score = row.get("human_score")
        if score is not None:
            if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 4:
                errors.append(f"row {i}: human_score must be an integer from 0 to 4")
            else:
                human_scores.append(score)
                item["human_score"] = score
        per_task[row["task"]].append(item)
        output_hashes.append(sha256(row["prediction"].encode("utf-8")))
    if not rows:
        errors.append("no test cases provided")
    if any(len(splits) > 1 for splits in source_splits.values()):
        errors.append("a source appears in multiple splits")
    if any(len(splits) > 1 for splits in group_splits.values()):
        errors.append("a document group appears in multiple splits")
    if errors:
        raise ValueError("\n".join(errors[:100]))
    task_summary = {}
    for task, values in sorted(per_task.items()):
        scores = [v["human_score"] for v in values if "human_score" in v]
        task_summary[task] = {
            "cases": len(values),
            "normalized_exact_match_rate": sum(v["exact_match"] for v in values) / len(values),
            "nonempty_prediction_rate": sum(v["prediction_nonempty"] for v in values) / len(values),
            "human_scored_cases": len(scores),
            "human_score_mean_0_to_4": sum(scores) / len(scores) if scores else None,
        }
    return {
        "schema_version": 1,
        "checkpoint_sha256": checkpoint_sha256,
        "cases": len(rows),
        "normalized_exact_match_rate": exact / len(rows),
        "nonempty_prediction_rate": nonempty / len(rows),
        "human_scored_cases": len(human_scores),
        "human_score_mean_0_to_4": sum(human_scores) / len(human_scores) if human_scores else None,
        "tasks": task_summary,
        "prediction_sha256": output_hashes,
        "raw_prompts_references_predictions_in_report": False,
        "used_for_training_or_checkpoint_selection": False,
        "limitations": [
            "Exact match is unsuitable as a sole measure for open-ended generation.",
            "Human scores require independent reviewers and the published rubric in docs/MKAOS_HUMAN_EVALUATION_PROTOCOL.md.",
            "This script validates supplied labels and split metadata; it cannot establish that a checkpoint actually produced predictions.",
            "Record Rust runtime version, checkpoint SHA-256, decoding parameters and evaluator identity alongside this report.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Local reviewed benchmark predictions JSONL")
    parser.add_argument("--checkpoint-sha256", required=True, help="SHA-256 of exact checkpoint tested by Rust")
    parser.add_argument("--output", required=True, type=Path, help="New local report path; will not overwrite")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-fA-F]{64}", args.checkpoint_sha256):
        parser.error("--checkpoint-sha256 must be a 64-character SHA-256")
    try:
        raw = args.input.read_bytes()
        rows = []
        for line_no, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f"line {line_no}: row must be an object")
            rows.append(item)
        report = evaluate(rows, checkpoint_sha256=args.checkpoint_sha256.lower())
        report["input_sha256"] = sha256(raw)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"Evaluation blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("Scoring completed; this does not by itself prove Turkish quality or checkpoint provenance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Run the Turkish quality task set against a local Ollama model and save raw results.

This is an evaluation aid, not an automatic model-quality certification. Output files may
contain model responses; choose a private local path and do not commit benchmark results
containing sensitive prompts or data.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from core.ollama_client import OllamaClient, validate_local_ollama_url


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--tasks", default="tests/fixtures/turkish_quality_tasks.json")
    parser.add_argument("--output", default="memory/benchmarks/latest.json")
    parser.add_argument("--limit", type=int, default=0, help="Optional positive task limit.")
    args = parser.parse_args()
    base_url = validate_local_ollama_url(args.base_url)
    tasks_path = Path(args.tasks)
    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
    if not isinstance(tasks, list):
        raise SystemExit("Task fixture must be a JSON list.")
    if args.limit > 0:
        tasks = tasks[:args.limit]
    client = OllamaClient(model=args.model, base_url=base_url)
    results = []
    for task in tasks:
        start = time.perf_counter()
        try:
            answer = client.chat(str(task["prompt_tr"]), temperature=0.0)
            error = None
        except Exception as exc:
            answer, error = "", type(exc).__name__
        results.append({
            "id": task.get("id"),
            "category": task.get("category"),
            "expected_checks": task.get("expected_checks", []),
            "answer": answer,
            "error": error,
            "latency_seconds": round(time.perf_counter() - start, 4),
        })
    report = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "runtime": "local_ollama",
        "base_url": base_url,
        "task_count": len(results),
        "successful_calls": sum(1 for item in results if item["error"] is None),
        "results": results,
        "limitations": [
            "No automatic semantic scoring is performed.",
            "Review expected checks manually or use a separately validated evaluator.",
            "Latency varies by hardware, model quantization, context and system load.",
        ],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(results)} local evaluation results to {output}")
    print("This report is not a model-quality certification.")
    return 0 if report["successful_calls"] == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

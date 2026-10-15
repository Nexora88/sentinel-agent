#!/usr/bin/env python3
"""Run a fixed Turkish quality smoke set against MKAOS and optional local Ollama.

The lexical checks and repetition detector are diagnostics, not semantic evaluation.
No remote model endpoint is accepted; all benchmark traffic stays on loopback.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "benchmarks" / "mkaos_quality_v1.json"
SYSTEM_PROMPT = "Answer accurately and concisely. Respond in Turkish when the user writes in Turkish."


def local_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "http" or parsed.username or parsed.password:
        raise ValueError("Only credential-free local http:// Ollama URLs are supported.")
    if (parsed.hostname or "").lower() not in {"localhost", "127.0.0.1", "::1", "ollama"}:
        raise ValueError("Remote model endpoints are blocked; use a local Ollama endpoint.")
    return value.rstrip("/")


def repeated_fourgrams(text: str) -> dict:
    words = re.findall(r"[^\W_]+", text.casefold(), flags=re.UNICODE)
    counts: dict[str, int] = {}
    for i in range(max(0, len(words) - 3)):
        gram = " ".join(words[i:i + 4])
        counts[gram] = counts.get(gram, 0) + 1
    repeated = {gram: count for gram, count in counts.items() if count >= 3}
    return {"repeated_fourgram_count": len(repeated), "repeated_fourgrams": repeated}


def evaluate(task: dict, answer: str) -> dict:
    normalized = answer.casefold()
    required_all = task.get("required_all", [])
    required_any = task.get("required_any", [])
    forbidden = task.get("forbidden", [])
    missing = [term for term in required_all if term.casefold() not in normalized]
    any_hit = not required_any or any(term.casefold() in normalized for term in required_any)
    found_forbidden = [term for term in forbidden if term.casefold() in normalized]
    bullet_count = sum(bool(re.match(r"^\s*(?:[-*•]|\d+[.)])\s+", line)) for line in answer.splitlines())
    checks = {
        "missing_required_terms": missing,
        "required_any_pass": any_hit,
        "forbidden_terms_found": found_forbidden,
        "word_count": len(re.findall(r"\b\w+\b", answer, flags=re.UNICODE)),
        "bullet_count": bullet_count,
        "repetition": repeated_fourgrams(answer),
    }
    checks["bullet_count_pass"] = (
        bullet_count == task["exact_bullets"] if "exact_bullets" in task else None
    )
    checks["minimum_words_pass"] = checks["word_count"] >= task.get("min_words", 0)
    checks["heuristic_pass"] = (
        not missing and any_hit and not found_forbidden
        and checks["minimum_words_pass"]
        and checks["bullet_count_pass"] is not False
        and checks["repetition"]["repeated_fourgram_count"] == 0
    )
    checks["warning"] = "Lexical smoke checks only; human review is required."
    return checks


def mkaos_once(binary: Path, model_dir: str, prompt: str, max_tokens: int, timeout: int) -> dict:
    env = dict(os.environ)
    env["MKAOS_SYSTEM_PROMPT"] = SYSTEM_PROMPT
    started = time.perf_counter()
    proc = subprocess.run(
        [str(binary), model_dir, prompt, str(max_tokens)],
        capture_output=True, text=True, timeout=timeout, env=env, cwd=ROOT,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    if proc.returncode:
        raise RuntimeError(f"MKAOS exit {proc.returncode}: {proc.stderr[-1500:]}")
    try:
        data = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        raise RuntimeError(f"MKAOS output was not metrics JSON: {proc.stdout[-1000:]}") from exc
    data["process_wall_ms"] = round(elapsed_ms, 3)
    return data


def ollama_once(base_url: str, model: str, prompt: str, timeout: int) -> dict:
    payload = json.dumps({
        "model": model, "prompt": prompt, "system": SYSTEM_PROMPT, "stream": True,
        "options": {"temperature": 0},
    }, ensure_ascii=False).encode("utf-8")
    request = Request(base_url + "/api/generate", data=payload,
                      headers={"Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    first_token_ms = None
    pieces: list[str] = []
    final: dict = {}
    try:
        with urlopen(request, timeout=timeout) as response:
            for raw in response:
                if not raw.strip():
                    continue
                item = json.loads(raw)
                piece = item.get("response", "")
                if piece:
                    pieces.append(piece)
                    if first_token_ms is None:
                        first_token_ms = (time.perf_counter() - started) * 1000
                final = item
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        raise RuntimeError(f"Ollama request failed: {type(exc).__name__}: {exc}") from exc
    total_ms = (time.perf_counter() - started) * 1000
    eval_ns = int(final.get("eval_duration", 0) or 0)
    return {
        "engine": "Ollama", "text": "".join(pieces),
        "first_token_ms": round(first_token_ms, 3) if first_token_ms is not None else None,
        "inference_total_ms": round(total_ms, 3),
        "generated_token_count": final.get("eval_count"),
        "tokens_per_second": round(final["eval_count"] / (eval_ns / 1e9), 3)
            if eval_ns > 0 and isinstance(final.get("eval_count"), int) else None,
        "model_load_ms": round(int(final.get("load_duration", 0) or 0) / 1e6, 3),
        "prompt_token_count": final.get("prompt_eval_count"),
        "process_wall_ms": round(total_ms, 3),
    }


def summarize(rows: list[dict]) -> list[dict]:
    summaries = []
    engines = sorted({row["engine"] for row in rows})
    for engine in engines:
        group = [row for row in rows if row["engine"] == engine]
        valid = [row for row in group if row["status"] == "ok"]
        latencies = [row["metrics"].get("inference_total_ms") for row in valid
                     if isinstance(row["metrics"].get("inference_total_ms"), (int, float))]
        tps = [row["metrics"].get("tokens_per_second") for row in valid
               if isinstance(row["metrics"].get("tokens_per_second"), (int, float))]
        summaries.append({
            "engine": engine, "tasks": len(group),
            "successful_runs": len(valid), "failed_runs": len(group) - len(valid),
            "heuristic_passes": sum(bool(row["checks"]["heuristic_pass"]) for row in valid),
            "heuristic_pass_rate": round(sum(bool(row["checks"]["heuristic_pass"]) for row in valid) / len(valid), 3) if valid else None,
            "median_inference_ms": round(statistics.median(latencies), 3) if latencies else None,
            "p95_inference_ms": sorted(latencies)[min(len(latencies)-1, int(0.95 * len(latencies)))] if latencies else None,
            "median_tokens_per_second": round(statistics.median(tps), 3) if tps else None,
            "repetition_flagged_runs": sum(row["checks"]["repetition"]["repeated_fourgram_count"] > 0 for row in valid),
        })
    return summaries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--mkaos-binary", default=str(ROOT / "engine/mkaos-hf-adapter/target/release/mkaos_generate"))
    parser.add_argument("--ollama-model")
    parser.add_argument("--ollama-url", default=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output", default="mkaos-quality-report.json")
    args = parser.parse_args()
    if not 1 <= args.runs <= 5:
        parser.error("--runs must be between 1 and 5")
    if args.max_new_tokens < 1 or args.timeout < 1:
        parser.error("--max-new-tokens and --timeout must be positive")
    binary = Path(args.mkaos_binary)
    if not binary.is_file():
        parser.error(f"MKAOS binary not found: {binary}")
    dataset_bytes = Path(args.dataset).read_bytes()
    dataset = json.loads(dataset_bytes)
    base_url = local_url(args.ollama_url) if args.ollama_model else None
    rows = []
    for task in dataset["tasks"]:
        for run_index in range(1, args.runs + 1):
            for engine in (["MKAOS", "Ollama"] if args.ollama_model else ["MKAOS"]):
                started = time.perf_counter()
                row = {"engine": engine, "task_id": task["id"], "category": task["category"], "run": run_index}
                try:
                    if engine == "MKAOS":
                        metrics = mkaos_once(binary, args.model_dir, task["prompt"], args.max_new_tokens, args.timeout)
                    else:
                        metrics = ollama_once(base_url, args.ollama_model, task["prompt"], args.timeout)
                    answer = str(metrics.get("text", ""))
                    row.update({"status": "ok", "metrics": metrics, "answer": answer,
                                "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
                                "checks": evaluate(task, answer)})
                except (RuntimeError, subprocess.TimeoutExpired, OSError, ValueError) as exc:
                    row.update({"status": "error", "error": f"{type(exc).__name__}: {exc}",
                                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3)})
                rows.append(row)
                print(f"{engine} | {task['id']} | run={run_index} | {row['status']}")
    report = {
        "schema_version": 1, "dataset_id": dataset["dataset_id"],
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system_prompt": SYSTEM_PROMPT, "model_dir": args.model_dir,
        "ollama_model": args.ollama_model, "runs_per_task": args.runs,
        "max_new_tokens": args.max_new_tokens, "results": rows,
        "summary": summarize(rows),
        "limitations": [
            "This is a fixed smoke suite with lexical checks, not expert semantic grading.",
            "A pass does not prove correctness, general intelligence, safety, or production readiness.",
            "MKAOS process wall time includes loading weights/tokenizer; inference_total_ms is the CLI's generation interval.",
            "This CI host is not the user's target device; repeat with scripts/device_validation.py and real device measurements."
        ],
    }
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if all(row["status"] == "ok" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())

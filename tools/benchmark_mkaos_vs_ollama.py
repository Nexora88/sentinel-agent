#!/usr/bin/env python3
"""Compare resident MKAOS and local Ollama steady-request latency without TTFT sampling."""
import argparse
import json
import subprocess
import threading
import time
import urllib.error
import urllib.request

SYSTEM_PROMPT = "Answer accurately and concisely. Respond in Turkish when the user writes in Turkish."
PROMPTS = [
    "In one sentence, what is photosynthesis?",
    "Bir cümleyle Türkiye'nin başkentini söyle.",
    "Explain the difference between weather and climate in two short sentences.",
    "Bir cümleyle asal sayıyı açıkla.",
]


def parse_memory_mb(value: str) -> float | None:
    try:
        number = value.strip().split()[0].split("/")[0]
        # docker stats returns e.g. '123.4MiB / 7.6GiB'; ps returns a numeric KiB value.
        import re
        match = re.fullmatch(r"([0-9.]+)\s*([KMGT]?i?B)?", number, re.IGNORECASE)
        if not match:
            return None
        amount = float(match.group(1))
        unit = (match.group(2) or "KiB").lower()
        factors = {
            "b": 1 / (1024 * 1024), "kb": 1 / 1024, "kib": 1 / 1024,
            "mb": 1, "mib": 1, "gb": 1024, "gib": 1024,
            "tb": 1024 * 1024, "tib": 1024 * 1024,
        }
        return amount * factors[unit]
    except (ValueError, IndexError, KeyError):
        return None


def sample_memory(stop_event: threading.Event, peak: list, *, process_name: str | None = None,
                  container_name: str | None = None) -> None:
    while not stop_event.is_set():
        try:
            if container_name:
                result = subprocess.run(
                    ["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", container_name],
                    capture_output=True, text=True, check=False, timeout=2,
                )
                value = parse_memory_mb(result.stdout.strip().split("/")[0]) if result.returncode == 0 else None
            else:
                result = subprocess.run(
                    ["ps", "-C", process_name or "mkaos_server", "-o", "rss="],
                    capture_output=True, text=True, check=False, timeout=2,
                )
                values = [int(x) for x in result.stdout.split() if x.isdigit()]
                value = sum(values) / 1024 if values else None
            if value is not None:
                peak[0] = max(peak[0], value)
        except (OSError, subprocess.TimeoutExpired):
            pass
        stop_event.wait(0.15)


def request_json(url: str, payload: dict, timeout: int = 600) -> tuple[dict, float]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except Exception as exc:
        raise RuntimeError(f"request to {url} failed: {exc}") from exc
    elapsed_ms = (time.perf_counter() - started) * 1000
    try:
        records = [line for line in raw.splitlines() if line.strip()]
        result = json.loads(records[-1])
    except (ValueError, IndexError) as exc:
        raise RuntimeError(f"invalid JSON response from {url}") from exc
    return result, elapsed_ms


def ollama_once(base_url: str, model: str, prompt: str, max_new_tokens: int) -> dict:
    peak = [0.0]
    stop = threading.Event()
    sampler = threading.Thread(
        target=sample_memory, args=(stop, peak), kwargs={"container_name": "ollama"}, daemon=True
    )
    sampler.start()
    try:
        result, total_ms = request_json(base_url.rstrip("/") + "/api/generate", {
            "model": model, "prompt": prompt, "system": SYSTEM_PROMPT, "stream": False,
            "options": {"temperature": 0.0, "num_predict": max_new_tokens},
        })
    finally:
        stop.set()
        sampler.join(timeout=2)
    eval_ns = int(result.get("eval_duration", 0) or 0)
    eval_count = int(result.get("eval_count", 0) or 0)
    return {
        "engine": "Ollama", "text": result.get("response", ""),
        "total_request_ms": round(total_ms, 2),
        "generated_tokens": eval_count,
        "tokens_per_second": eval_count / (eval_ns / 1e9) if eval_ns > 0 else None,
        "prompt_tokens": result.get("prompt_eval_count"),
        "peak_container_memory_mb_sampled": round(peak[0], 2) if peak[0] else None,
        "model_load_ms": int(result.get("load_duration", 0) or 0) / 1e6,
    }


def mkaos_once(base_url: str, prompt: str, max_new_tokens: int) -> dict:
    peak = [0.0]
    stop = threading.Event()
    sampler = threading.Thread(
        target=sample_memory, args=(stop, peak), kwargs={"process_name": "mkaos_server"}, daemon=True
    )
    sampler.start()
    try:
        result, total_ms = request_json(base_url.rstrip("/") + "/api/generate", {
            "model": "mkaos-local", "prompt": prompt, "system": SYSTEM_PROMPT,
            "options": {
                "num_predict": max_new_tokens, "temperature": 0.0,
                "top_p": 0.9, "repeat_penalty": 1.10,
            },
        })
    finally:
        stop.set()
        sampler.join(timeout=2)
    eval_ns = int(result.get("eval_duration", 0) or 0)
    eval_count = int(result.get("eval_count", 0) or 0)
    return {
        "engine": "MKAOS resident server", "text": result.get("response", ""),
        "total_request_ms": round(total_ms, 2),
        "generated_tokens": eval_count,
        "tokens_per_second": eval_count / (eval_ns / 1e9) if eval_ns > 0 else None,
        "prompt_tokens": result.get("prompt_eval_count"),
        "peak_process_memory_mb_sampled": round(peak[0], 2) if peak[0] else None,
        "model_load_ms": int(result.get("load_duration", 0) or 0) / 1e6,
        "prefix_cache_hit": result.get("mkaos_prefix_cache_hit"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mkaos-url", default="http://127.0.0.1:11435")
    parser.add_argument("--ollama-model", required=True)
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--max-new-tokens", type=int, default=32)
    args = parser.parse_args()
    if not 1 <= args.runs <= 10:
        raise SystemExit("--runs must be between 1 and 10")
    if not 1 <= args.max_new_tokens <= 512:
        raise SystemExit("--max-new-tokens must be between 1 and 512")

    results = []
    for run in range(args.runs):
        for prompt in PROMPTS:
            mkaos = mkaos_once(args.mkaos_url, prompt, args.max_new_tokens)
            ollama = ollama_once(args.ollama_url, args.ollama_model, prompt, args.max_new_tokens)
            row = {
                "run": run + 1, "prompt": prompt, "mkaos": mkaos, "ollama": ollama,
                "exact_text_match": mkaos.get("text", "").strip() == ollama.get("text", "").strip(),
            }
            results.append(row)
            print(json.dumps(row, ensure_ascii=False))

    report = {
        "schema_version": 2, "mode": "resident_steady_request_latency",
        "ollama_model": args.ollama_model, "mkaos_url": args.mkaos_url,
        "runs": args.runs, "max_new_tokens": args.max_new_tokens,
        "prompt_count_per_run": len(PROMPTS), "system_prompt": SYSTEM_PROMPT,
        "results": results,
        "metrics_note": "This report measures complete request latency, generated tokens/s and sampled memory. It intentionally does not measure TTFT; run the dedicated TTFT test only after the resident-service, quality and target-device gates.",
        "warning": "Exact text equality is not a semantic quality metric. Review the fixed quality report and target-device results before changing the default provider.",
    }
    with open("mkaos-ollama-benchmark.json", "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
        file.write("\n")
    print("Wrote mkaos-ollama-benchmark.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

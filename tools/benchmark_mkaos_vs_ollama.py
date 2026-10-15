#!/usr/bin/env python3
"""Same-device MKAOS-vs-Ollama smoke benchmark; no performance claims without its output.

Example:
  python tools/benchmark_mkaos_vs_ollama.py --model-dir models/smollm2-135m-instruct \
    --ollama-model smollm2:135m-instruct --runs 3
Requires a running local Ollama API, a downloaded MKAOS model, and Linux /usr/bin/time.
"""
import argparse
import json
import re
import subprocess
import threading
import time
import urllib.request

SYSTEM_PROMPT = "Answer accurately and concisely. Respond in Turkish when the user writes in Turkish."

PROMPTS = [
    "In one sentence, what is photosynthesis?",
    "Bir cümleyle Türkiye'nin başkentini söyle.",
    "Explain the difference between weather and climate in two short sentences.",
    "Bir cümleyle asal sayıyı açıkla.",
]


def sample_ollama_rss(stop_event: threading.Event, peak: list) -> None:
    while not stop_event.is_set():
        try:
            ps = subprocess.run(
                ["ps", "-C", "ollama", "-o", "rss="],
                capture_output=True, text=True, check=False,
            )
            values = [int(x) for x in ps.stdout.split() if x.isdigit()]
            if values:
                peak[0] = max(peak[0], sum(values))
        except OSError:
            pass
        stop_event.wait(0.1)


def ollama_once(base_url: str, model: str, prompt: str) -> dict:
    payload = json.dumps({
        "model": model, "prompt": prompt,
        "system": SYSTEM_PROMPT, "stream": True,
        "options": {"temperature": 0},
    }).encode()
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/generate", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    start = time.perf_counter()
    first_token_s = None
    pieces = []
    final = {}
    peak_rss_kb = [0]
    stop_sampling = threading.Event()
    sampler = threading.Thread(target=sample_ollama_rss, args=(stop_sampling, peak_rss_kb), daemon=True)
    sampler.start()
    try:
        response = urllib.request.urlopen(request, timeout=600)
        with response:
            for raw_line in response:
                if not raw_line.strip():
                    continue
                record = json.loads(raw_line)
                piece = record.get("response", "")
                if piece:
                    pieces.append(piece)
                    if first_token_s is None:
                        first_token_s = time.perf_counter() - start
                final = record
    except Exception as exc:
        raise RuntimeError(f"Ollama API request failed: {exc}") from exc
    finally:
        stop_sampling.set()
        sampler.join(timeout=1)
    total_s = time.perf_counter() - start
    eval_ns = int(final.get("eval_duration", 0) or 0)
    eval_count = int(final.get("eval_count", 0) or 0)
    return {
        "engine": "Ollama", "text": "".join(pieces),
        "first_token_ms": None if first_token_s is None else first_token_s * 1000,
        "total_ms": total_s * 1000, "generated_tokens": eval_count,
        "tokens_per_second": eval_count / (eval_ns / 1e9) if eval_ns > 0 else None,
        "prompt_tokens": final.get("prompt_eval_count"),
        "peak_process_rss_mb_sampled": peak_rss_kb[0] / 1024 if peak_rss_kb[0] else None,
        "model_load_ms": (int(final.get("load_duration", 0) or 0) / 1e6),
    }


def mkaos_once(model_dir: str, prompt: str, max_new_tokens: int) -> dict:
    command = [
        "/usr/bin/time", "-v", "cargo", "run", "--release", "--quiet",
        "--manifest-path", "engine/mkaos-hf-adapter/Cargo.toml",
        "--bin", "mkaos_generate", "--", model_dir, prompt, str(max_new_tokens),
    ]
    child_env = dict(__import__("os").environ)
    child_env["MKAOS_SYSTEM_PROMPT"] = SYSTEM_PROMPT
    result = subprocess.run(command, capture_output=True, text=True, timeout=900, env=child_env)
    if result.returncode:
        raise RuntimeError(f"MKAOS run failed: {result.stderr[-4000:]}")
    try:
        metrics = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        raise RuntimeError(f"MKAOS did not return metrics JSON: {result.stdout!r}") from exc
    match = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", result.stderr)
    metrics["peak_process_rss_mb"] = int(match.group(1)) / 1024 if match else None
    metrics["end_to_end_ms_including_model_load"] = metrics.get("model_load_ms", 0.0) + metrics.get("inference_total_ms", 0.0)
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--ollama-model", required=True)
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--max-new-tokens", type=int, default=32)
    args = parser.parse_args()
    if args.runs < 1 or args.runs > 10:
        raise SystemExit("--runs must be between 1 and 10")
    if args.max_new_tokens < 1 or args.max_new_tokens > 512:
        raise SystemExit("--max-new-tokens must be between 1 and 512")
    results = []
    for run in range(args.runs):
        for prompt in PROMPTS:
            mkaos = mkaos_once(args.model_dir, prompt, args.max_new_tokens)
            ollama = ollama_once(args.ollama_url, args.ollama_model, prompt)
            row = {
                "run": run + 1, "prompt": prompt,
                "mkaos": mkaos, "ollama": ollama,
                "exact_text_match": mkaos.get("text", "").strip() == ollama.get("text", "").strip(),
            }
            results.append(row)
            print(json.dumps(row, ensure_ascii=False))
    report = {
        "schema_version": 1,
        "model_dir": args.model_dir,
        "ollama_model": args.ollama_model,
        "runs": args.runs,
        "max_new_tokens": args.max_new_tokens,
        "prompt_count_per_run": len(PROMPTS),
        "system_prompt": SYSTEM_PROMPT,
        "results": results,
        "warning": "Greedy output equality is not a full quality metric. Compare task correctness, latency, token/s and RAM over repeated runs before removing Ollama.",
    }
    with open("mkaos-ollama-benchmark.json", "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
        file.write("\n")
    print("Wrote mkaos-ollama-benchmark.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

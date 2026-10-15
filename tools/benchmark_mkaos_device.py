#!/usr/bin/env python3
"""Repeatable cold-start and warm-request benchmark for a local MKAOS HTTP server.

This tool records measurements; it does not claim that a model is sovereign or good.
Run it on the target physical device and preserve the JSON report with the source revision.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import json
import os
import platform
import shlex
import signal
import statistics
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_PROMPTS = [
    {"id": "tr_capital", "prompt": "Türkiye'nin başkenti neresidir? Kısa ve doğru cevap ver."},
    {"id": "tr_explain", "prompt": "Fotosentezi Türkçe olarak iki cümlede açıkla."},
    {"id": "tr_reason", "prompt": "Bir çiftçi toprağın kuru olduğunu ölçtü. Sulama kararı verirken hangi iki ek bilgiyi kontrol etmelidir?"},
]


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = max(0.0, min(float(len(ordered) - 1), (len(ordered) - 1) * p))
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    value = ordered[lower] if lower == upper else ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
    return round(value, 3)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def machine_metadata() -> dict[str, Any]:
    result: dict[str, Any] = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "architecture": platform.machine(),
        "processor": platform.processor() or None,
        "cpu_count_logical": os.cpu_count(),
    }
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("MemTotal:"):
                result["ram_total_mib"] = round(int(line.split()[1]) / 1024, 2)
                break
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith(("model name", "hardware")):
                result["cpu_model"] = line.split(":", 1)[-1].strip()
                break
    try:
        result["git_commit"] = subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=3
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        result["git_commit"] = None
    try:
        gpu = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            check=True, capture_output=True, text=True, timeout=3,
        ).stdout.strip()
        result["nvidia_gpu"] = gpu or None
    except (OSError, subprocess.SubprocessError):
        result["nvidia_gpu"] = None
    return result


def request_json(url: str, payload: dict[str, Any], timeout: float) -> tuple[dict[str, Any], float]:
    request = urllib.request.Request(
        url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    elapsed_ms = (time.perf_counter() - started) * 1000
    lines = [line for line in raw.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"empty response from {url}")
    try:
        result = json.loads(lines[-1])
    except ValueError as exc:
        raise RuntimeError(f"invalid JSON response from {url}") from exc
    if not isinstance(result, dict):
        raise RuntimeError(f"response from {url} must be a JSON object")
    return result, elapsed_ms


def wait_healthy(url: str, process: subprocess.Popen[str], timeout: float) -> float:
    started = time.perf_counter()
    deadline = started + timeout
    last_error = "health endpoint did not respond"
    while time.perf_counter() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"server exited early (code {process.returncode}); check server log")
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if 200 <= response.status < 300:
                    return (time.perf_counter() - started) * 1000
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            last_error = str(exc)
        time.sleep(0.1)
    raise TimeoutError(f"server health timeout after {timeout}s: {last_error}")


def launch(command: list[str], env: dict[str, str]) -> subprocess.Popen[str]:
    return subprocess.Popen(
        command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        text=True, env=env, start_new_session=True,
    )


def stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass


def sample_rss_mib(pid: int) -> float | None:
    status = Path(f"/proc/{pid}/status")
    try:
        for line in status.read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return round(int(line.split()[1]) / 1024, 3)
    except (OSError, ValueError, IndexError):
        return None
    return None


def payload_for(prompt: str, max_new_tokens: int) -> dict[str, Any]:
    return {
        "model": "mkaos-local",
        "prompt": prompt,
        "system": "Türkçe sorulara Türkçe, doğru ve açık cevap ver. Bilmediğin bilgiyi uydurma.",
        "options": {"num_predict": max_new_tokens, "temperature": 0.0, "top_p": 0.9},
    }


def summarize(rows: list[dict[str, Any]], key: str) -> dict[str, float | None]:
    values = [float(row[key]) for row in rows if isinstance(row.get(key), (int, float))]
    return {"count": len(values), "median_ms": percentile(values, 0.5), "p95_ms": percentile(values, 0.95)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-command", required=True, help="server command, split with shell-like quoting; do not use shell=True")
    parser.add_argument("--health-url", default="http://127.0.0.1:11435/health")
    parser.add_argument("--generate-url", default="http://127.0.0.1:11435/api/generate")
    parser.add_argument("--runs", type=int, default=3, help="number of cold-start trials")
    parser.add_argument("--warm-runs", type=int, default=5, help="number of requests to measure after one warm-up")
    parser.add_argument("--max-new-tokens", type=int, default=48)
    parser.add_argument("--startup-timeout-seconds", type=float, default=180)
    parser.add_argument("--request-timeout-seconds", type=float, default=300)
    parser.add_argument("--model-manifest", type=Path, help="manifest file whose SHA-256 identifies the model artifact")
    parser.add_argument("--tokenizer-file", type=Path, help="tokenizer file whose SHA-256 identifies the tokenizer")
    parser.add_argument("--output", type=Path, default=Path("artifacts/mkaos-device-benchmark.json"))
    parser.add_argument("--network-isolation", choices=["not-verified", "container-network-none", "host-firewall-verified"], default="not-verified",
                        help="declarative evidence label; choose a verified value only when the runner actually enforces it")
    args = parser.parse_args()
    if not 1 <= args.runs <= 20 or not 1 <= args.warm_runs <= 100:
        parser.error("--runs must be 1..20 and --warm-runs must be 1..100")
    if not 1 <= args.max_new_tokens <= 512:
        parser.error("--max-new-tokens must be 1..512")

    command = shlex.split(args.server_command)
    if not command:
        parser.error("--server-command cannot be empty")
    env = os.environ.copy()
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["NO_PROXY"] = "127.0.0.1,localhost"
    env["no_proxy"] = env["NO_PROXY"]

    prompts = DEFAULT_PROMPTS
    cold_rows: list[dict[str, Any]] = []
    warm_rows: list[dict[str, Any]] = []
    errors: list[str] = []

    # Each cold trial launches a fresh server process; warm samples share one resident process.
    for trial in range(1, args.runs + 1):
        process = launch(command, env)
        try:
            startup_ms = wait_healthy(args.health_url, process, args.startup_timeout_seconds)
            prompt = prompts[(trial - 1) % len(prompts)]
            response, first_request_ms = request_json(
                args.generate_url, payload_for(prompt["prompt"], args.max_new_tokens), args.request_timeout_seconds
            )
            cold_rows.append({
                "trial": trial, "prompt_id": prompt["id"], "startup_to_healthy_ms": round(startup_ms, 3),
                "first_request_wall_ms": round(first_request_ms, 3),
                "startup_plus_first_request_ms": round(startup_ms + first_request_ms, 3),
                "generated_tokens": response.get("eval_count"),
                "tokens_per_second": response.get("tokens_per_second"),
                "model_load_ms": (float(response.get("load_duration", 0) or 0) / 1e6),
                "server_rss_mib_after_first_request": sample_rss_mib(process.pid),
                "response_text": response.get("response", ""),
            })
        except Exception as exc:
            errors.append(f"cold trial {trial}: {type(exc).__name__}: {exc}")
        finally:
            stop_process(process)

    resident = launch(command, env)
    try:
        resident_startup_ms = wait_healthy(args.health_url, resident, args.startup_timeout_seconds)
        warmup_prompt = prompts[0]
        request_json(args.generate_url, payload_for(warmup_prompt["prompt"], args.max_new_tokens), args.request_timeout_seconds)
        for index in range(args.warm_runs):
            prompt = prompts[index % len(prompts)]
            rss_samples: list[float] = []
            stop_sample = threading.Event()

            def sample_loop() -> None:
                while not stop_sample.is_set():
                    value = sample_rss_mib(resident.pid)
                    if value is not None:
                        rss_samples.append(value)
                    stop_sample.wait(0.05)

            sampler = threading.Thread(target=sample_loop, daemon=True)
            sampler.start()
            try:
                response, elapsed_ms = request_json(
                    args.generate_url, payload_for(prompt["prompt"], args.max_new_tokens), args.request_timeout_seconds
                )
            finally:
                stop_sample.set()
                sampler.join(timeout=1)
            warm_rows.append({
                "request": index + 1, "prompt_id": prompt["id"], "wall_ms": round(elapsed_ms, 3),
                "generated_tokens": response.get("eval_count"),
                "tokens_per_second": response.get("tokens_per_second"),
                "model_load_ms": float(response.get("load_duration", 0) or 0) / 1e6,
                "peak_sampled_server_rss_mib": max(rss_samples) if rss_samples else sample_rss_mib(resident.pid),
                "response_text": response.get("response", ""),
            })
    except Exception as exc:
        errors.append(f"warm phase: {type(exc).__name__}: {exc}")
        resident_startup_ms = None
    finally:
        stop_process(resident)

    report: dict[str, Any] = {
        "schema_version": 1,
        "benchmark": "mkaos_same_device_cold_and_warm",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "command": command,
        "fixed_settings": {
            "runs": args.runs, "warm_runs": args.warm_runs, "max_new_tokens": args.max_new_tokens,
            "prompts": prompts, "temperature": 0.0, "offline_env_flags": {
                "HF_HUB_OFFLINE": env["HF_HUB_OFFLINE"], "TRANSFORMERS_OFFLINE": env["TRANSFORMERS_OFFLINE"]
            },
            "network_isolation_claim": args.network_isolation,
        },
        "hardware_and_build": machine_metadata(),
        "artifact_hashes": {
            "model_manifest_sha256": sha256_file(args.model_manifest) if args.model_manifest and args.model_manifest.is_file() else None,
            "tokenizer_sha256": sha256_file(args.tokenizer_file) if args.tokenizer_file and args.tokenizer_file.is_file() else None,
            "rustflags": env.get("RUSTFLAGS"), "cargo_profile": env.get("CARGO_PROFILE"),
        },
        "cold_start": {
            "summary": {
                "startup_to_healthy_ms": summarize(cold_rows, "startup_to_healthy_ms"),
                "first_request_wall_ms": summarize(cold_rows, "first_request_wall_ms"),
                "startup_plus_first_request_ms": summarize(cold_rows, "startup_plus_first_request_ms"),
            },
            "results": cold_rows,
        },
        "warm_requests": {
            "resident_startup_ms": round(resident_startup_ms, 3) if resident_startup_ms is not None else None,
            "summary": {"wall_ms": summarize(warm_rows, "wall_ms")},
            "results": warm_rows,
        },
        "errors": errors,
        "limitations": [
            "Network isolation is not enforced by this script; it records the runner's declared evidence label.",
            "RSS is sampled from /proc and may miss short peaks; use OS-level peak-memory tooling for formal comparisons.",
            "Generated text requires human quality review; this benchmark does not certify factuality or model ownership.",
            "Cold-start numbers are only comparable when hardware, power mode, model, tokenizer, prompt set, build flags and runtime settings match.",
            "TTFT is intentionally not inferred from whole-response HTTP latency; measure it only with token-stream timestamps after correctness gates pass.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output), "cold_trials": len(cold_rows), "warm_requests": len(warm_rows),
        "cold_startup_plus_first_request_ms": report["cold_start"]["summary"]["startup_plus_first_request_ms"],
        "warm_request_wall_ms": report["warm_requests"]["summary"]["wall_ms"], "errors": errors,
    }, ensure_ascii=False, indent=2))
    return 1 if errors or len(cold_rows) != args.runs or len(warm_rows) != args.warm_runs else 0


if __name__ == "__main__":
    raise SystemExit(main())

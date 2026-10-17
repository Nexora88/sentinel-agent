#!/usr/bin/env python3
"""Local-only MKAOS training diagnostics; does not change settings or start training.

Reports host RAM, PyTorch/CUDA runtime, GPU memory, estimated model/training memory,
JSONL corpus read/tokenization throughput, and optional native CLI first-token latency.
All benchmark inputs and outputs stay on this machine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def available_ram() -> int | None:
    try:
        import psutil
        return int(psutil.virtual_memory().available)
    except ImportError:
        try:
            return int(os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE"))
        except (AttributeError, OSError, ValueError):
            return None


def model_parameters(vocab: int, hidden: int, layers: int, heads: int,
                     kv_heads: int, intermediate: int) -> int:
    if min(vocab, hidden, layers, heads, kv_heads, intermediate) < 1:
        raise ValueError("All model dimensions must be positive.")
    if hidden % heads or heads % kv_heads:
        raise ValueError("hidden must divide heads and heads must divide evenly by kv_heads.")
    kv_width = hidden // heads * kv_heads
    per_layer = 2 * hidden + 2 * hidden * hidden + 2 * hidden * kv_width + 3 * hidden * intermediate
    return vocab * hidden * 2 + layers * per_layer + hidden


def estimate_training_bytes(params: int, batch: int, seq: int, hidden: int,
                            layers: int, intermediate: int, activation_bytes: int = 4) -> int:
    if min(params, batch, seq, hidden, layers, intermediate, activation_bytes) < 1:
        raise ValueError("All memory estimate inputs must be positive.")
    # Approximation: parameters + gradients + Adam states, plus coarse activation allowance.
    return params * 16 + batch * seq * (8 * hidden + 3 * intermediate) * layers * activation_bytes


def probe_runtime() -> dict[str, Any]:
    result: dict[str, Any] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count_logical": os.cpu_count(),
        "available_host_ram_bytes": available_ram(),
        "pytorch_available": False,
        "pytorch_version": None,
        "cuda_build_version": None,
        "cuda_available": False,
        "device_name": None,
        "device_count": 0,
        "gpu_total_memory_bytes": None,
        "gpu_free_memory_bytes": None,
        "gpu_allocated_memory_bytes": None,
        "gpu_reserved_memory_bytes": None,
        "rocm_version": None,
    }
    try:
        import torch
    except ImportError:
        result["runtime_note"] = "PyTorch missing from this Python environment; no CUDA check possible."
        return result
    result["pytorch_available"] = True
    result["pytorch_version"] = str(torch.__version__)
    result["cuda_build_version"] = getattr(torch.version, "cuda", None)
    result["rocm_version"] = getattr(torch.version, "hip", None)
    try:
        result["cuda_available"] = bool(torch.cuda.is_available())
        if result["cuda_available"]:
            result["device_count"] = int(torch.cuda.device_count())
            result["device_name"] = str(torch.cuda.get_device_name(0))
            props = torch.cuda.get_device_properties(0)
            result["gpu_total_memory_bytes"] = int(getattr(props, "total_memory", 0)) or None
            try:
                free, total = torch.cuda.mem_get_info(0)
                result["gpu_free_memory_bytes"] = int(free)
                result["gpu_total_memory_bytes"] = int(total)
            except Exception as exc:
                result["gpu_memory_probe_note"] = type(exc).__name__
            result["gpu_allocated_memory_bytes"] = int(torch.cuda.memory_allocated(0))
            result["gpu_reserved_memory_bytes"] = int(torch.cuda.memory_reserved(0))
    except Exception as exc:
        result["accelerator_probe_error"] = type(exc).__name__ + ": " + str(exc)[:300]
    result["mps_available"] = bool(
        hasattr(torch, "backends") and hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
    )
    return result


def corpus_benchmark(path: Path, sample_limit: int) -> dict[str, Any]:
    start = time.perf_counter()
    file_bytes = path.stat().st_size
    digest = hashlib.sha256()
    lines = 0
    json_bytes = 0
    text_bytes = 0
    tokens = 0
    malformed = 0
    with path.open("rb") as f:
        for raw in f:
            digest.update(raw)
            json_bytes += len(raw)
            if not raw.strip():
                continue
            lines += 1
            if sample_limit and lines > sample_limit:
                break
            try:
                item = json.loads(raw)
                text = item.get("text") if isinstance(item, dict) else None
                if not isinstance(text, str) or not text:
                    malformed += 1
                    continue
                encoded = text.encode("utf-8")
                text_bytes += len(encoded)
                tokens += len(encoded) + 1  # byte tokenizer + EOS
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                malformed += 1
    elapsed = max(time.perf_counter() - start, 1e-9)
    return {
        "path": str(path),
        "file_size_bytes": file_bytes,
        "sha256_of_bytes_read": digest.hexdigest(),
        "sample_limit": sample_limit or None,
        "records_seen_including_malformed": lines,
        "valid_text_utf8_bytes": text_bytes,
        "byte_tokens_including_eos": tokens,
        "malformed_records": malformed,
        "elapsed_seconds": round(elapsed, 6),
        "jsonl_read_and_parse_bytes_per_second": round(json_bytes / elapsed, 2),
        "valid_text_bytes_per_second": round(text_bytes / elapsed, 2),
        "byte_tokens_per_second": round(tokens / elapsed, 2),
        "note": "Local file read + JSON parse + UTF-8 byte counting; not remote download speed or training-step throughput.",
    }


def native_ttft(args: argparse.Namespace) -> dict[str, Any]:
    binary = args.native_cli
    checkpoint = args.checkpoint
    if not binary or not checkpoint:
        return {"status": "skipped", "reason": "Pass both --native-cli and --checkpoint to measure native CLI first-token wall latency."}
    binary_path, checkpoint_path = Path(binary), Path(checkpoint)
    if not binary_path.is_file() or not checkpoint_path.is_file():
        return {"status": "blocked", "reason": "Native CLI or checkpoint path does not exist."}
    digest = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    timings = []
    errors = []
    for _ in range(args.ttft_repeats):
        command = [
            str(binary_path), "--checkpoint", str(checkpoint_path), "--sha256", digest,
            "--heads", str(args.heads), "--kv-heads", str(args.kv_heads),
            "--max-seq", str(args.sequence_length), "--max-new-tokens", "1",
            "--prompt", args.prompt,
        ]
        started = time.perf_counter()
        try:
            run = subprocess.run(command, capture_output=True, text=True, timeout=args.timeout_seconds, check=False)
        except subprocess.TimeoutExpired:
            errors.append("timeout")
            continue
        wall_ms = (time.perf_counter() - started) * 1000
        if run.returncode:
            errors.append((run.stderr or f"exit={run.returncode}")[-1000:])
        else:
            timings.append(wall_ms)
    if not timings:
        return {"status": "failed", "checkpoint_sha256": digest, "errors": errors}
    ordered = sorted(timings)
    return {
        "status": "measured",
        "checkpoint_sha256": digest,
        "prompt_utf8_bytes": len(args.prompt.encode("utf-8")),
        "generated_tokens_per_run": 1,
        "repeats_succeeded": len(timings),
        "repeats_failed": len(errors),
        "first_token_wall_latency_ms_each": [round(x, 3) for x in timings],
        "first_token_wall_latency_ms_min": round(min(timings), 3),
        "first_token_wall_latency_ms_median": round(ordered[len(ordered) // 2], 3),
        "definition": "Process wall time from launch to one-token completion; includes process startup, checkpoint read/hash, model load and generation. It is not warm in-process TTFT.",
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, help="Optional local JSONL corpus to benchmark; never uploaded.")
    parser.add_argument("--sample-limit", type=int, default=0, help="0 reads the whole corpus; otherwise read at most this many non-empty records.")
    parser.add_argument("--vocab-size", type=int, default=257)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--kv-heads", type=int, default=2)
    parser.add_argument("--intermediate-size", type=int, default=128)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--sequence-length", type=int, default=128)
    parser.add_argument("--native-cli", help="Path to a locally built mkaos-generate binary.")
    parser.add_argument("--checkpoint", help="Path to a locally generated .mkaosw checkpoint.")
    parser.add_argument("--prompt", default="MKAOS yerli yapay zekâ testi.")
    parser.add_argument("--ttft-repeats", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    args = parser.parse_args()
    if args.sample_limit < 0 or args.ttft_repeats < 1 or args.timeout_seconds < 1:
        parser.error("sample-limit must be >= 0; ttft-repeats and timeout-seconds must be positive.")
    if min(args.batch_size, args.sequence_length) < 1:
        parser.error("batch-size and sequence-length must be positive.")

    report: dict[str, Any] = {
        "report_schema": "mkaos-local-diagnostics-v1",
        "mode": "diagnostics_only_no_training_no_network",
        "hardware_runtime": probe_runtime(),
    }
    try:
        params = model_parameters(args.vocab_size, args.hidden_size, args.layers, args.heads,
                                  args.kv_heads, args.intermediate_size)
        estimated = estimate_training_bytes(params, args.batch_size, args.sequence_length,
                                            args.hidden_size, args.layers, args.intermediate_size)
        report["model_config"] = {
            "vocab_size": args.vocab_size, "hidden_size": args.hidden_size,
            "layers": args.layers, "heads": args.heads, "kv_heads": args.kv_heads,
            "intermediate_size": args.intermediate_size, "batch_size": args.batch_size,
            "sequence_length": args.sequence_length, "parameter_count_estimate": params,
            "training_memory_estimate_bytes": estimated,
            "memory_estimate_warning": "Approximation, not a peak-memory guarantee; actual kernels, precision, allocator and optimizer affect usage.",
        }
    except ValueError as exc:
        parser.error(str(exc))
    if args.corpus:
        try:
            report["corpus_throughput"] = corpus_benchmark(args.corpus, args.sample_limit)
        except OSError as exc:
            report["corpus_throughput"] = {"status": "failed", "error": str(exc)}
    report["native_ttft"] = native_ttft(args)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("corpus_throughput", {}).get("status") != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

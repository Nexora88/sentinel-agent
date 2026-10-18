#!/usr/bin/env python3
"""Plan (but do not launch) an MKAOS from-scratch training run.

This tool performs estimates only. It never downloads data, loads a corpus into RAM,
starts training, or bypasses the source/provenance gate in train_mkaos_from_scratch.py.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def parameter_count(vocab_size: int, hidden_size: int, layers: int,
                    heads: int, kv_heads: int, intermediate_size: int) -> int:
    if min(vocab_size, hidden_size, layers, heads, kv_heads, intermediate_size) < 1:
        raise ValueError("All model dimensions must be positive.")
    if hidden_size % heads or heads % kv_heads:
        raise ValueError("hidden_size must divide heads and heads must divide evenly by kv_heads.")
    kv_width = hidden_size // heads * kv_heads
    per_layer = (
        2 * hidden_size
        + hidden_size * hidden_size
        + 2 * hidden_size * kv_width
        + hidden_size * hidden_size
        + 3 * hidden_size * intermediate_size
    )
    return vocab_size * hidden_size * 2 + layers * per_layer + hidden_size


def available_ram_bytes() -> int | None:
    try:
        import psutil
        return int(psutil.virtual_memory().available)
    except ImportError:
        try:
            return int(os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE"))
        except (AttributeError, OSError, ValueError):
            return None


def hardware_report() -> dict:
    report: dict = {
        "available_host_ram_bytes": available_ram_bytes(),
        "free_disk_bytes_at_repo": shutil.disk_usage(ROOT).free,
        "pytorch_available": False,
        "cuda_available": False,
        "cuda_devices": [],
    }
    try:
        import torch
        report["pytorch_available"] = True
        report["torch_version"] = torch.__version__
        report["cuda_available"] = bool(torch.cuda.is_available())
        if report["cuda_available"]:
            for index in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(index)
                report["cuda_devices"].append({
                    "index": index,
                    "name": props.name,
                    "total_vram_bytes": int(props.total_memory),
                })
    except ImportError:
        pass
    return report


def gib(n: int | None) -> float | None:
    return round(n / (1024 ** 3), 2) if n is not None else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-billions", type=float, default=10.0,
                        help="Architectural target in billions of parameters (planning only; default 10).")
    parser.add_argument("--corpus", type=Path, help="Optional existing corpus path; only its file size is read.")
    parser.add_argument("--sequence-length", type=int, default=4096)
    parser.add_argument("--micro-batch-size", type=int, default=1)
    parser.add_argument("--shards", type=int, default=1,
                        help="Effective parameter/optimizer sharding degree; assumes ideal even sharding.")
    parser.add_argument("--tokens-per-parameter", type=float, default=20.0,
                        help="Planning heuristic only, not a guarantee or hard requirement.")
    args = parser.parse_args()
    if not 1 <= args.target_billions <= 200:
        parser.error("target-billions must be between 1 and 200")
    if min(args.sequence_length, args.micro_batch_size, args.shards) < 1:
        parser.error("sequence length, micro-batch size, and shards must be positive")
    if args.tokens_per_parameter <= 0:
        parser.error("tokens-per-parameter must be positive")

    # 10B is the default architectural target only; this tool does not create or train it.
    # Keep vocab fixed to current byte tokenizer to make this estimate comparable.
    # The 10B profile uses the exact checked-in dimensions; other values use a
    # rounded 50-layer family and then recompute the true parameter count.
    if args.target_billions == 10.0:
        width, layers, intermediate = 4096, 50, 13312
    else:
        layers = 50
        raw_width = max(1024, int((args.target_billions * 1_000_000_000 / (layers * 10)) ** 0.5))
        lower_width = max(1024, (raw_width // 1024) * 1024)
        width_candidates = (lower_width, lower_width + 1024)
        width = min(
            width_candidates,
            key=lambda candidate: abs(
                parameter_count(257, candidate, layers, candidate // 128,
                                max(1, candidate // 1024), int(candidate * 2.6667))
                - args.target_billions * 1_000_000_000
            ),
        )
        intermediate = int(width * 2.6667)
    config = {
        "profile": f"mkaos-{args.target_billions:g}b-scratch-target",
        "vocab_size": 257,
        "hidden_size": width,
        "layers": layers,
        "heads": width // 128,
        "kv_heads": max(1, width // 1024),
        "intermediate_size": intermediate,
        "sequence_length": args.sequence_length,
        "micro_batch_size": args.micro_batch_size,
        "effective_optimizer_shards": args.shards,
        "tokenizer_note": "Current byte-level tokenizer (vocab 257); inefficient for natural language is a known limitation.",
    }
    params = parameter_count(
        config["vocab_size"], config["hidden_size"], config["layers"],
        config["heads"], config["kv_heads"], config["intermediate_size"],
    )
    if not 0.8 * args.target_billions <= params / 1e9 <= 1.2 * args.target_billions:
        parser.error("rounded architecture is outside 20% of target; adjust the planner profile")
    # Baseline full-training-state estimate: weights + gradients + AdamW moments/master state.
    training_state_bytes = params * 16
    per_shard_state_bytes = (training_state_bytes + args.shards - 1) // args.shards
    # A simple lower-bound activation estimate; attention workspaces, fragmentation,
    # communication buffers and runtime overhead are not included.
    activation_bytes = (
        args.micro_batch_size * args.sequence_length
        * (8 * config["hidden_size"] + 3 * config["intermediate_size"])
        * config["layers"] * 2
    )
    f32_checkpoint_bytes = params * 4
    bf16_weights_bytes = params * 2
    report = {
        "mode": "estimate-only; training was not started",
        "architecture": config,
        "exact_parameter_count_for_current_implementation": params,
        "status": f"architecture_target_only; no {args.target_billions:g}B checkpoint exists or was trained",
        "parameter_count_billions": round(params / 1e9, 4),
        "estimated_f32_checkpoint_gib": gib(f32_checkpoint_bytes),
        "estimated_bf16_weights_gib": gib(bf16_weights_bytes),
        "estimated_training_state_gib_total_before_sharding": gib(training_state_bytes),
        "estimated_training_state_gib_per_shard": gib(per_shard_state_bytes),
        "rough_activation_allowance_gib_not_including_attention_workspaces": gib(activation_bytes),
        "estimated_target_tokens_at_tokens_per_parameter_heuristic": int(params * args.tokens_per_parameter),
        "tokens_per_parameter_heuristic": args.tokens_per_parameter,
        "hardware": hardware_report(),
        "limitations": [
            "Memory values are planning estimates, not a fit guarantee; real peak memory can be higher.",
            "Sharding estimate assumes ideal even sharding and does not model communication or replicated state.",
            "Large targets require measured distributed-training capacity; this planner does not prove the trainer or selected hardware can fit the model.",
            f"For the computed profile, BF16 weights alone are about {gib(bf16_weights_bytes):.2f} GiB; Adam-style training-state estimate is about {gib(training_state_bytes):.2f} GiB before activation, communication and implementation overhead.",
            "The 200 GB file size is not the same as usable, deduplicated training tokens.",
            "Current byte tokenizer means UTF-8 byte count is only a rough upper-bound proxy, not a measured tokenizer token count.",
            "This planner does not read or download corpus contents and does not approve sources or manifests.",
            "Training remains blocked unless the existing provenance and source-register gates pass.",
            "Cloud compute, model downloads, and paid services are never provisioned by this planner.",
        ],
    }
    if args.corpus:
        try:
            size = args.corpus.stat().st_size
        except OSError as exc:
            parser.error(f"cannot stat corpus path: {exc}")
        report["corpus"] = {
            "path": str(args.corpus),
            "file_size_bytes": size,
            "file_size_gib": gib(size),
            "utf8_byte_count_upper_bound_before_jsonl_overhead_and_filtering": size,
            "estimated_tokens_from_file_size": None,
            "note": "Exact token count requires parsing and applying the tokenizer to the approved corpus; this command deliberately does not load it.",
        }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


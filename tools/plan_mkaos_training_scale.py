#!/usr/bin/env python3
"""Estimate MKAOS training scale without allocating a model or starting training."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.train_mkaos_from_scratch import estimate_parameter_count, estimate_training_memory_bytes

def gib(value: int | float) -> float:
    return value / (1024 ** 3)

def plan(profile: dict) -> dict:
    model, training = profile["model"], profile["training"]
    params = estimate_parameter_count(int(profile["tokenizer"]["vocab_size"]), int(model["hidden_size"]), int(model["layers"]), int(model["heads"]), int(model["kv_heads"]), int(model["intermediate_size"]))
    activation_bytes = 2 if training.get("precision") in {"fp16", "bf16"} else 4
    estimate = estimate_training_memory_bytes(params, int(training["batch_size"]), int(training["sequence_length"]), int(model["hidden_size"]), int(model["layers"]), int(model["intermediate_size"]), activation_bytes=activation_bytes)
    activation_estimate = int(training["batch_size"]) * int(training["sequence_length"]) * (8 * int(model["hidden_size"]) + 3 * int(model["intermediate_size"])) * int(model["layers"]) * activation_bytes
    hw = profile["hardware"]
    return {
        "profile_id": profile["profile_id"],
        "planning_only": True,
        "training_started": False,
        "source_rights_approved": False,
        "parameter_count": params,
        "parameter_count_billions": round(params / 1_000_000_000, 4),
        "optimizer_and_parameter_state_gib_estimate_unsharded": round(gib(params * 16), 2),
        "activation_gib_estimate": round(gib(activation_estimate), 2),
        "total_estimated_memory_gib_unsharded": round(gib(estimate), 2),
        "estimated_memory_is_not_peak_guarantee": True,
        "configured_accelerator_memory_minimum_gib": hw.get(
            "accelerator_memory_gib_minimum_per_gpu",
            hw.get("accelerator_memory_gib_minimum_planning")),
        "configured_accelerator_memory_recommended_gib": hw.get(
            "accelerator_memory_gib_recommended_per_gpu",
            hw.get("accelerator_memory_gib_recommended")),
        "configured_accelerator_count_minimum": hw.get("accelerator_count_minimum_planning"),
        "configured_accelerator_count_recommended": hw.get("accelerator_count_recommended"),
        "configured_system_ram_gib_minimum": hw["system_ram_gib_minimum_planning"],
        "current_trainer_gaps": [
            "the conservative preflight does not calculate a validated per-rank memory budget for optimizer-state sharding",
            "DDP replicates model parameters and gradients; current optimizer-state sharding is not FSDP or ZeRO-3",
            "byte-level tokenization is inefficient for Turkish at scale",
            "no 10B throughput, recovery, quality, or cloud-cost measurement exists",
        ],
        "next_gates": [
            "complete source-specific legal, privacy, attribution and training-use review",
            "approve model-weight distribution separately or keep checkpoints private",
            "prepare a locally held corpus with exact hashes, privacy screening and independent splits",
            "implement and verify per-rank memory accounting before a 10B run",
            "pin cloud vendor, region, machine topology, budget cap, retention and access controls",
            "run a small measured distributed pilot with checkpoint recovery before scaling",
        ],
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--output", type=Path, help="Optional new JSON report path; existing files are never overwritten")
    args = parser.parse_args()
    try:
        profile = json.loads(args.profile.read_text(encoding="utf-8"))
        if profile.get("schema_version") != 1: raise ValueError("Unsupported profile schema_version")
        rendered = json.dumps(plan(profile), ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as handle: handle.write(rendered)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot create scale plan: {exc}", file=sys.stderr); return 2
    print(rendered, end="")
    print("WARNING: planning output only; it does not authorize training or clear data rights.", file=sys.stderr)
    return 0

if __name__ == "__main__": raise SystemExit(main())


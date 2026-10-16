#!/usr/bin/env python3
"""Train an original MKAOS decoder from random initialization; never downloads a model.

Corpus format: JSONL, one object per line: {"sample_id":"...", "text":"..."}.
A separately human-approved provenance manifest assigns each sample to a split.
The manifest's SHA-256 must match the UTF-8 bytes of each text field exactly.
Requires PyTorch only for training; no hub client, pretrained weights, or remote API.
"""
from __future__ import annotations

import argparse
from array import array
import hashlib
import json
import math
import os
import random
import struct
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Any

# Make repository modules importable when invoked as `python tools/train_mkaos_from_scratch.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MAGIC = b"MKAOSW1\0"
ROOT = Path(__file__).resolve().parents[1]
TOKENIZER_CONTRACT_PATH = ROOT / "spec" / "mkaos-tokenizer-v1.json"
TOKENIZER_CONTRACT = json.loads(TOKENIZER_CONTRACT_PATH.read_text(encoding="utf-8"))
if TOKENIZER_CONTRACT.get("format") != "mkaos-byte-v1" or TOKENIZER_CONTRACT.get("vocab_size") != 257 or TOKENIZER_CONTRACT.get("eos_id") != 256:
    raise RuntimeError(f"Unsupported or inconsistent shared tokenizer contract: {TOKENIZER_CONTRACT_PATH}")
VOCAB_SIZE = TOKENIZER_CONTRACT["vocab_size"]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Hash a potentially large corpus file without loading it into an extra byte buffer."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def estimate_parameter_count(vocab_size: int, hidden_size: int, layers: int,
                             heads: int, kv_heads: int, intermediate_size: int) -> int:
    """Exact parameter count for this implementation's untied GQA/SwiGLU decoder."""
    if min(vocab_size, hidden_size, layers, heads, kv_heads, intermediate_size) < 1:
        raise ValueError("Model dimensions must be positive")
    if hidden_size % heads or heads % kv_heads:
        raise ValueError("hidden_size must divide heads and heads must divide evenly by kv_heads")
    kv_width = hidden_size // heads * kv_heads
    per_layer = (
        2 * hidden_size  # two RMSNorm weights
        + hidden_size * hidden_size  # Q
        + 2 * hidden_size * kv_width  # K and V
        + hidden_size * hidden_size  # attention output
        + 3 * hidden_size * intermediate_size  # SwiGLU gate, up, down
    )
    return vocab_size * hidden_size * 2 + layers * per_layer + hidden_size


def estimate_training_memory_bytes(parameter_count: int, batch_size: int,
                                   sequence_length: int, hidden_size: int,
                                   layers: int, intermediate_size: int,
                                   activation_bytes: int = 4) -> int:
    """Conservative planning estimate, not a guarantee of peak allocator usage.

    Parameter/gradient/AdamW-state allowance is 16 bytes per parameter. Activation
    allowance is intentionally approximate; allocator fragmentation and attention
    workspaces can increase the real peak.
    """
    if min(parameter_count, batch_size, sequence_length, hidden_size, layers,
           intermediate_size, activation_bytes) < 1:
        raise ValueError("Memory-estimate inputs must be positive")
    parameter_and_optimizer = parameter_count * 16
    activations = (
        batch_size * sequence_length * (8 * hidden_size + 3 * intermediate_size)
        * layers * activation_bytes
    )
    return parameter_and_optimizer + activations


def read_corpus(path: Path) -> dict[str, str]:
    samples: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(item, dict) or not isinstance(item.get("sample_id"), str):
                raise ValueError(f"{path}:{line_no}: sample_id must be a string")
            if not isinstance(item.get("text"), str) or not item["text"]:
                raise ValueError(f"{path}:{line_no}: text must be a non-empty string")
            sample_id = item["sample_id"]
            if sample_id in samples:
                raise ValueError(f"{path}:{line_no}: duplicate sample_id {sample_id!r}")
            samples[sample_id] = item["text"]
    if not samples:
        raise ValueError("Corpus contains no samples")
    return samples


def validate_corpus_against_manifest(corpus: dict[str, str], manifest: Any) -> dict[str, list[str]]:
    """Fail closed if corpus content does not match approved manifest metadata."""
    if not isinstance(manifest, dict) or not isinstance(manifest.get("records"), list):
        raise ValueError("Manifest must contain a records array")
    split_texts: dict[str, list[str]] = {"train": [], "validation": [], "test": []}
    seen: set[str] = set()
    for record in manifest["records"]:
        if not isinstance(record, dict):
            raise ValueError("Every manifest record must be an object")
        sample_id = record.get("sample_id")
        if not isinstance(sample_id, str) or sample_id in seen:
            raise ValueError(f"Invalid or duplicate manifest sample_id: {sample_id!r}")
        seen.add(sample_id)
        if sample_id not in corpus:
            raise ValueError(f"Manifest sample {sample_id!r} has no corpus text")
        text = corpus[sample_id]
        digest = sha256(text.encode("utf-8"))
        if record.get("sha256") != digest:
            raise ValueError(f"Content SHA-256 mismatch for sample {sample_id!r}")
        split = record.get("split")
        if split not in split_texts:
            raise ValueError(f"Invalid split for sample {sample_id!r}: {split!r}")
        split_texts[split].append(text)
    extras = set(corpus) - seen
    if extras:
        raise ValueError(f"Corpus contains samples absent from manifest: {sorted(extras)[:5]}")
    missing = [name for name, values in split_texts.items() if not values]
    if missing:
        raise ValueError("Missing non-empty split(s): " + ", ".join(missing))
    return split_texts


def encode_documents(texts: list[str]) -> array:
    # Use compact unsigned 16-bit token storage: Python int lists can consume tens of
    # gigabytes for a large byte-level corpus. EOS=256 fits in array('H').
    ids = array("H")
    for text in texts:
        ids.frombytes(b"")  # keep array construction explicit and portable
        ids.extend(text.encode("utf-8"))
        ids.append(256)
    return ids


def write_mkaos_checkpoint(path: Path, tensors: dict[str, Any]) -> str:
    """Write Rust MKAOSW1 format: name + rows + cols + little-endian f32 matrix."""
    payload = bytearray(MAGIC)
    payload.extend(struct.pack("<I", len(tensors)))
    for name in sorted(tensors):
        matrix = tensors[name].detach().to(device="cpu", dtype=__import__("torch").float32).contiguous()
        if matrix.ndim != 2:
            raise ValueError(f"Tensor {name} must be 2-D, got {matrix.ndim}-D")
        name_bytes = name.encode("utf-8")
        if not name_bytes or len(name_bytes) > 256:
            raise ValueError(f"Invalid tensor name length: {name!r}")
        rows, cols = matrix.shape
        if rows < 1 or cols < 1:
            raise ValueError(f"Empty tensor is not allowed: {name}")
        payload.extend(struct.pack("<H", len(name_bytes)))
        payload.extend(name_bytes)
        payload.extend(struct.pack("<II", rows, cols))
        payload.extend(matrix.numpy().astype("<f4", copy=False).tobytes(order="C"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return sha256(bytes(payload))


def learning_rate_for_step(
    base_learning_rate: float,
    step: int,
    total_steps: int,
    warmup_steps: int = 0,
    min_learning_rate_ratio: float = 0.1,
) -> float:
    """Linear warmup followed by cosine decay; deterministic and independent of PyTorch."""
    if base_learning_rate <= 0:
        raise ValueError("base_learning_rate must be positive")
    if total_steps < 1 or not 1 <= step <= total_steps:
        raise ValueError("step must be in 1..total_steps")
    if warmup_steps < 0 or warmup_steps > total_steps:
        raise ValueError("warmup_steps must be in 0..total_steps")
    if not 0 < min_learning_rate_ratio <= 1:
        raise ValueError("min_learning_rate_ratio must be in (0, 1]")
    if warmup_steps and step <= warmup_steps:
        return base_learning_rate * step / warmup_steps
    decay_denominator = max(1, total_steps - warmup_steps - 1)
    progress = min(1.0, max(0.0, (step - warmup_steps - 1) / decay_denominator))
    cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
    ratio = min_learning_rate_ratio + (1.0 - min_learning_rate_ratio) * cosine
    return base_learning_rate * ratio


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, type=Path, help="Approved local JSONL text corpus")
    parser.add_argument("--manifest", required=True, type=Path, help="Human-reviewed provenance manifest")
    parser.add_argument("--source-register", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "mkaos" / "source-register.json", help="Source register; every used source must be explicitly approved")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--experimental-local-only", action="store_true", help="Opt into owner-authorized local experiments; this does not approve third-party data or authorize checkpoint distribution")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--sequence-length", type=int, default=128)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--kv-heads", type=int, default=2)
    parser.add_argument("--intermediate-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=1, help="micro-batches per optimizer step; lowers activation memory")
    parser.add_argument("--warmup-steps", type=int, default=0, help="linear learning-rate warmup steps; 0 disables warmup")
    parser.add_argument("--min-learning-rate-ratio", type=float, default=0.1, help="cosine schedule floor as a fraction of --learning-rate")
    parser.add_argument("--seed", type=int, default=20261016)
    parser.add_argument("--gradient-checkpointing", action="store_true", help="Recompute decoder-layer activations during backward to reduce activation memory.")
    parser.add_argument("--resume-from", type=Path, help="Resume from a trusted local trainer checkpoint saved at an epoch boundary.")
    parser.add_argument("--distributed", action="store_true", help="Enable torchrun DDP when WORLD_SIZE > 1; launch with torchrun.")
    parser.add_argument("--optimizer-state-sharding", action="store_true", help="Shard AdamW optimizer states across distributed ranks using ZeroRedundancyOptimizer.")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto",
                        help="Training device; auto prefers a locally available CUDA/ROCm runtime.")
    parser.add_argument("--precision", choices=("auto", "fp32", "fp16", "bf16"), default="auto",
                        help="Training precision; auto uses fp32 on CPU and the safest supported mixed precision on CUDA.")
    args = parser.parse_args()

    if min(args.epochs, args.batch_size, args.sequence_length, args.hidden_size,
           args.layers, args.heads, args.kv_heads, args.intermediate_size,
           args.gradient_accumulation_steps) < 1:
        parser.error("sizes, epochs, batch size and gradient accumulation must be positive")
    if args.warmup_steps < 0:
        parser.error("warmup-steps cannot be negative")
    if not (0 < args.min_learning_rate_ratio <= 1):
        parser.error("min-learning-rate-ratio must be in (0, 1]")
    if args.hidden_size % args.heads or args.heads % args.kv_heads:
        parser.error("hidden-size must divide heads, and heads must divide evenly by kv-heads")
    if (args.hidden_size // args.heads) % 2:
        parser.error("hidden-size / heads must be even for rotary embeddings")
    if not (0 < args.learning_rate < 1):
        parser.error("learning-rate must be between 0 and 1")

    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        # The strict governance validator is the canonical gate; no training starts on failure.
        from validate_mkaos_training_manifest import validate_manifest
        manifest_messages = validate_manifest(manifest, experimental_local_only=args.experimental_local_only)
        errors = [m for m in manifest_messages if not m.startswith("Metadata checks passed")]
        if errors:
            raise ValueError("Manifest validation failed:\n- " + "\n- ".join(errors))
        source_registry = json.loads(args.source_register.read_text(encoding="utf-8"))
        from core.mkaos_corpus_gate import validate_experimental_local_manifest, validate_source_registry
        if args.experimental_local_only:
            source_messages = validate_experimental_local_manifest(manifest, source_registry)
            source_errors = [m for m in source_messages if not m.startswith("Experimental local-only gate passed")]
            if source_errors:
                raise ValueError("Experimental local-only gate failed")
            print("EXPERIMENTAL LOCAL-ONLY MODE: " + source_messages[0])
        else:
            source_messages = validate_source_registry(manifest, source_registry)
            source_errors = [m for m in source_messages if not m.startswith("Source register checks passed")]
            if source_errors:
                raise ValueError("Source register validation failed:\\n- " + "\\n- ".join(source_errors))
            print("Source gate: " + source_messages[0])
        corpus = read_corpus(args.corpus)
        splits = validate_corpus_against_manifest(corpus, manifest)
        corpus_file_sha256 = sha256_file(args.corpus)
        manifest_file_sha256 = sha256_file(args.manifest)
    except (OSError, json.JSONDecodeError, ValueError, ImportError) as exc:
        print(f"ERROR: training data gate failed: {exc}", file=sys.stderr)
        return 2

    train_ids = encode_documents(splits["train"])
    val_ids = encode_documents(splits["validation"])
    test_ids = encode_documents(splits["test"])
    if len(train_ids) < args.sequence_length + 1 or len(val_ids) < args.sequence_length + 1:
        print("ERROR: train and validation data each need at least sequence-length + 1 byte tokens", file=sys.stderr)
        return 2
    if len(test_ids) < args.sequence_length + 1:
        print("ERROR: independent test data needs at least sequence-length + 1 byte tokens", file=sys.stderr)
        return 2

    train_start_count = len(range(0, len(train_ids) - args.sequence_length, args.sequence_length))
    if distributed:
        train_start_count = (train_start_count // (world_size * args.batch_size)) * args.batch_size
    train_batch_count = math.ceil(train_start_count / args.batch_size)
    if train_batch_count < 1:
        print("ERROR: training split is too small for the configured batch size and distributed world size.", file=sys.stderr)
        return 2
    optimizer_steps_per_epoch = math.ceil(train_batch_count / args.gradient_accumulation_steps)
    total_optimizer_steps = args.epochs * optimizer_steps_per_epoch
    if args.warmup_steps > total_optimizer_steps:
        print("ERROR: warmup-steps cannot exceed the total optimizer-step count", file=sys.stderr)
        return 2

    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
        from core.hardware_backends import probe_training_runtime
        hardware_runtime_probe = probe_training_runtime(torch)
    except ImportError:
        print("ERROR: PyTorch is required for training. Install a locally approved PyTorch build; no model downloads are used.", file=sys.stderr)
        return 2

    distributed_env_world_size = int(os.environ.get("WORLD_SIZE", "1"))
    distributed = args.distributed and distributed_env_world_size > 1
    if args.optimizer_state_sharding and not distributed:
        print("ERROR: --optimizer-state-sharding requires --distributed with torchrun WORLD_SIZE > 1.", file=sys.stderr)
        return 2
    if distributed:
        import torch.distributed as dist
        local_rank = int(os.environ.get("LOCAL_RANK", "0"))
        dist_backend = "nccl" if torch.cuda.is_available() and args.device != "cpu" else "gloo"
        dist.init_process_group(backend=dist_backend, init_method="env://")
        rank = dist.get_rank()
        world_size = dist.get_world_size()
    else:
        rank, world_size, local_rank = 0, 1, 0
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    cuda_available = bool(torch.cuda.is_available())
    if args.device == "cuda" and not cuda_available:
        print("ERROR: --device cuda was requested but no compatible local CUDA/ROCm training runtime is available.", file=sys.stderr)
        return 2
    device = torch.device("cuda", local_rank) if distributed and args.device != "cpu" and cuda_available else torch.device("cuda" if (args.device == "cuda" or (args.device == "auto" and cuda_available)) else "cpu")
    if device.type == "cuda":
        torch.cuda.set_device(device)
        torch.cuda.manual_seed_all(args.seed + rank)
    d, nh, nkh = args.hidden_size, args.heads, args.kv_heads
    hd, kv_width = d // nh, d // nh * nkh
    intermediate = args.intermediate_size

    if args.precision == "auto":
        if device.type != "cuda":
            precision = "fp32"
        elif hasattr(torch.cuda, "is_bf16_supported") and torch.cuda.is_bf16_supported():
            precision = "bf16"
        else:
            precision = "fp16"
    else:
        precision = args.precision
    if device.type != "cuda" and precision != "fp32":
        print("ERROR: fp16/bf16 training is currently enabled only for the CUDA/ROCm training path.", file=sys.stderr)
        return 2
    if device.type == "cuda" and precision == "bf16" and not (
        hasattr(torch.cuda, "is_bf16_supported") and torch.cuda.is_bf16_supported()
    ):
        print("ERROR: bf16 was requested but the detected accelerator does not report bf16 support.", file=sys.stderr)
        return 2

    parameter_count = estimate_parameter_count(
        VOCAB_SIZE, d, args.layers, nh, nkh, intermediate
    )
    activation_bytes = 2 if device.type == "cuda" and precision in {"fp16", "bf16"} else 4
    estimated_memory_bytes = estimate_training_memory_bytes(
        parameter_count, args.batch_size, args.sequence_length, d, args.layers,
        intermediate, activation_bytes=activation_bytes
    )
    try:
        if device.type == "cuda":
            available_memory_bytes = int(torch.cuda.mem_get_info(device)[0])
        else:
            try:
                import psutil
                available_memory_bytes = int(psutil.virtual_memory().available)
            except ImportError:
                try:
                    available_memory_bytes = int(
                        os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
                    )
                except (AttributeError, OSError, ValueError):
                    # If the OS cannot expose available RAM, report the limitation;
                    # never pretend an unknown budget is a measured value.
                    available_memory_bytes = 0
    except Exception as exc:
        print(f"ERROR: could not safely determine available memory: {type(exc).__name__}", file=sys.stderr)
        return 2
    if available_memory_bytes and estimated_memory_bytes > int(available_memory_bytes * 0.80):
        print(
            "ERROR: memory preflight blocked training before model allocation. "
            f"Estimated requirement={estimated_memory_bytes} bytes; "
            f"available={available_memory_bytes} bytes; policy limit=80%. "
            "Use a smaller architecture/sequence/batch, gradient accumulation, or a larger verified machine.",
            file=sys.stderr,
        )
        return 2

    if device.type == "cuda":
        backend_runtime = "rocm" if getattr(torch.version, "hip", None) else "cuda"
        device_name = torch.cuda.get_device_name(device)
    else:
        backend_runtime = "cpu"
        device_name = "CPU"
    print(json.dumps({
        "event": "training_preflight",
        "device": str(device),
        "backend_runtime": backend_runtime,
        "device_name": device_name,
        "precision": precision,
        "parameter_count": parameter_count,
        "estimated_training_memory_bytes": estimated_memory_bytes,
        "available_memory_bytes_before_model": available_memory_bytes or None,
        "memory_estimate_is_not_a_peak_usage_guarantee": True,
        "hardware_runtime_probe": hardware_runtime_probe,
    }, ensure_ascii=False))

    class MkaosLayer(nn.Module):
        def __init__(self):
            super().__init__()
            self.input_norm = nn.Parameter(torch.ones(d))
            self.q_proj = nn.Parameter(torch.empty(d, d))
            self.k_proj = nn.Parameter(torch.empty(d, kv_width))
            self.v_proj = nn.Parameter(torch.empty(d, kv_width))
            self.o_proj = nn.Parameter(torch.empty(d, d))
            self.post_attention_norm = nn.Parameter(torch.ones(d))
            self.gate_proj = nn.Parameter(torch.empty(d, intermediate))
            self.up_proj = nn.Parameter(torch.empty(d, intermediate))
            self.down_proj = nn.Parameter(torch.empty(intermediate, d))
            for p in (self.q_proj, self.k_proj, self.v_proj, self.o_proj,
                      self.gate_proj, self.up_proj, self.down_proj):
                nn.init.normal_(p, mean=0.0, std=0.02)

        @staticmethod
        def norm(x, weight):
            return x * torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + 1e-5) * weight

        @staticmethod
        def rope(x):
            # Match the Rust engine's split-half RoPE exactly.
            length = x.shape[-2]
            half = x.shape[-1] // 2
            positions = torch.arange(length, device=x.device, dtype=x.dtype)
            inv = 1.0 / (10000.0 ** (torch.arange(half, device=x.device, dtype=x.dtype) * 2 / x.shape[-1]))
            angles = torch.outer(positions, inv)
            cos, sin = angles.cos()[None, None, :, :], angles.sin()[None, None, :, :]
            first, second = x[..., :half], x[..., half:]
            return torch.cat((first * cos - second * sin, second * cos + first * sin), dim=-1)

        def forward(self, x):
            b, length, _ = x.shape
            residual = x
            z = self.norm(x, self.input_norm)
            q = (z @ self.q_proj).view(b, length, nh, hd).transpose(1, 2)
            k = (z @ self.k_proj).view(b, length, nkh, hd).transpose(1, 2)
            v = (z @ self.v_proj).view(b, length, nkh, hd).transpose(1, 2)
            q, k = self.rope(q), self.rope(k)
            # Expand KV heads to query-head groups; mathematically equivalent to GQA.
            repeat = nh // nkh
            k = k.repeat_interleave(repeat, dim=1)
            v = v.repeat_interleave(repeat, dim=1)
            # PyTorch SDPA can dispatch to fused/flash attention kernels on compatible
            # CUDA/ROCm builds, avoiding the explicit quadratic score/mask tensors.
            attended = F.scaled_dot_product_attention(
                q, k, v, attn_mask=None, dropout_p=0.0, is_causal=True
            ).transpose(1, 2).contiguous().view(b, length, d)
            x = residual + attended @ self.o_proj
            residual = x
            z = self.norm(x, self.post_attention_norm)
            return residual + (F.silu(z @ self.gate_proj) * (z @ self.up_proj)) @ self.down_proj

    class MkaosFromScratch(nn.Module):
        def __init__(self):
            super().__init__()
            self.token_embedding = nn.Embedding(VOCAB_SIZE, d)
            self.layers = nn.ModuleList([MkaosLayer() for _ in range(args.layers)])
            self.final_norm = nn.Parameter(torch.ones(d))
            self.lm_head = nn.Parameter(torch.empty(d, VOCAB_SIZE))
            nn.init.normal_(self.token_embedding.weight, mean=0.0, std=0.02)
            nn.init.normal_(self.lm_head, mean=0.0, std=0.02)

        def forward(self, tokens):
            x = self.token_embedding(tokens)
            for layer in self.layers:
                if args.gradient_checkpointing and self.training and torch.is_grad_enabled():
                    from torch.utils.checkpoint import checkpoint
                    x = checkpoint(layer, x, use_reentrant=False)
                else:
                    x = layer(x)
            x = x * torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + 1e-5) * self.final_norm
            return x @ self.lm_head

    def batches(ids: array, shuffle: bool):
        starts = list(range(0, len(ids) - args.sequence_length, args.sequence_length))
        if shuffle:
            random.shuffle(starts)
        if distributed:
            # Drop only the tail needed to give every rank the same number of batches.
            usable = (len(starts) // (world_size * args.batch_size)) * world_size * args.batch_size
            starts = starts[:usable][rank::world_size]
        for offset in range(0, len(starts), args.batch_size):
            chunk = starts[offset:offset + args.batch_size]
            if not chunk:
                continue
            xx = torch.tensor([list(ids[s:s + args.sequence_length]) for s in chunk], dtype=torch.long, device=device)
            yy = torch.tensor([list(ids[s + 1:s + args.sequence_length + 1]) for s in chunk], dtype=torch.long, device=device)
            yield xx, yy

    resume_config = {
        "hidden_size": d,
        "layers": args.layers,
        "heads": nh,
        "kv_heads": nkh,
        "intermediate_size": intermediate,
        "sequence_length": args.sequence_length,
        "batch_size": args.batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "seed": args.seed,
        "learning_rate": args.learning_rate,
        "warmup_steps": args.warmup_steps,
        "min_learning_rate_ratio": args.min_learning_rate_ratio,
        "total_optimizer_steps": total_optimizer_steps,
        "gradient_checkpointing": args.gradient_checkpointing,
        "optimizer_state_sharding": args.optimizer_state_sharding,
        "precision": precision,
        "corpus_sha256": corpus_file_sha256,
        "manifest_sha256": manifest_file_sha256,
    }
    model = MkaosFromScratch().to(device)
    if distributed:
        from torch.nn.parallel import DistributedDataParallel
        model = DistributedDataParallel(model, device_ids=[local_rank] if device.type == "cuda" else None)
    if args.optimizer_state_sharding:
        from torch.distributed.optim import ZeroRedundancyOptimizer
        optimizer = ZeroRedundancyOptimizer(model.parameters(), optimizer_class=torch.optim.AdamW, lr=args.learning_rate)
    else:
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    scaler = torch.cuda.amp.GradScaler(
        enabled=(device.type == "cuda" and precision == "fp16")
    )

    def autocast_context():
        if device.type != "cuda" or precision == "fp32":
            return nullcontext()
        dtype = torch.float16 if precision == "fp16" else torch.bfloat16
        return torch.autocast(device_type="cuda", dtype=dtype)
    best_val = float("inf")
    best_state = None
    history = []
    global_step = 0
    start_epoch = 0
    checkpoint_dir = args.output_dir / "trainer-checkpoints"
    if args.resume_from:
        try:
            # Checkpoints contain Python/PyTorch pickle data: resume only from a trusted local file.
            saved = torch.load(args.resume_from, map_location="cpu", weights_only=False)
            if saved.get("format_version") != 1 or saved.get("tokenizer_sha256") != sha256(TOKENIZER_CONTRACT_PATH.read_bytes()):
                raise ValueError("checkpoint format or tokenizer contract mismatch")
            if saved.get("training_config") != resume_config:
                raise ValueError("resume configuration, corpus hash, or manifest hash does not match the checkpoint")
            model_to_save = model.module if hasattr(model, "module") else model
            model_to_save.load_state_dict(saved["model_state"])
            optimizer.load_state_dict(saved["optimizer_state"])
            scaler.load_state_dict(saved.get("scaler_state", {}))
            start_epoch = int(saved["epoch"]) + 1
            global_step = int(saved["global_step"])
            best_val = float(saved["best_validation_loss"])
            best_state = saved.get("best_state")
            history = list(saved.get("history", []))
            random.setstate(saved["python_rng_state"])
            torch.set_rng_state(saved["torch_rng_state"])
            if device.type == "cuda" and saved.get("cuda_rng_state") is not None:
                torch.cuda.set_rng_state_all(saved["cuda_rng_state"])
            print(json.dumps({"event": "checkpoint_resumed", "epoch": start_epoch, "global_step": global_step, "path": str(args.resume_from)}))
        except (OSError, RuntimeError, KeyError, TypeError, ValueError) as exc:
            print(f"ERROR: could not safely resume checkpoint: {exc}", file=sys.stderr)
            return 2
    for epoch in range(start_epoch, args.epochs):
        model.train()
        train_losses = []
        optimizer.zero_grad(set_to_none=True)
        for batch_index, (xx, yy) in enumerate(batches(train_ids, True)):
            with autocast_context():
                loss = F.cross_entropy(model(xx).reshape(-1, VOCAB_SIZE), yy.reshape(-1))
            if not torch.isfinite(loss):
                raise RuntimeError("Non-finite training loss; aborting without checkpoint export")
            group_start = (batch_index // args.gradient_accumulation_steps) * args.gradient_accumulation_steps
            group_size = min(args.gradient_accumulation_steps, train_batch_count - group_start)
            scaler.scale(loss / group_size).backward()
            train_losses.append(float(loss.detach().cpu()))
            batch_number = batch_index + 1
            if batch_number % args.gradient_accumulation_steps == 0 or batch_number == train_batch_count:
                global_step += 1
                learning_rate = learning_rate_for_step(
                    args.learning_rate, global_step, total_optimizer_steps,
                    args.warmup_steps, args.min_learning_rate_ratio,
                )
                for group in optimizer.param_groups:
                    group["lr"] = learning_rate
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
        model.eval()
        val_losses = []
        with torch.no_grad():
            for xx, yy in batches(val_ids, False):
                with autocast_context():
                    val_loss_batch = F.cross_entropy(model(xx).reshape(-1, VOCAB_SIZE), yy.reshape(-1))
                val_losses.append(float(val_loss_batch.cpu()))
        if not train_losses or not val_losses:
            raise RuntimeError("No train/validation batches; increase corpus size or reduce sequence length")
        val_loss = sum(val_losses) / len(val_losses)
        history.append({"epoch": epoch + 1, "train_loss": sum(train_losses) / len(train_losses), "validation_loss": val_loss})
        print(json.dumps(history[-1], ensure_ascii=False))
        if val_loss < best_val:
            best_val = val_loss
            model_for_state = model.module if hasattr(model, "module") else model
            best_state = {key: value.detach().cpu().clone() for key, value in model_for_state.state_dict().items()}

        # Epoch-boundary checkpoints include optimizer/scaler/RNG state for resumption.
        if args.optimizer_state_sharding:
            optimizer.consolidate_state_dict(to=0)
        if rank == 0:
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            model_for_state = model.module if hasattr(model, "module") else model
            trainer_state = {
                "format_version": 1,
                "epoch": epoch,
                "global_step": global_step,
                "model_state": model_for_state.state_dict(),
                "optimizer_state": optimizer.state_dict(),
                "scaler_state": scaler.state_dict(),
                "best_validation_loss": best_val,
                "best_state": best_state,
                "history": history,
                "python_rng_state": random.getstate(),
                "torch_rng_state": torch.get_rng_state(),
                "cuda_rng_state": torch.cuda.get_rng_state_all() if device.type == "cuda" else None,
                "tokenizer_sha256": sha256(TOKENIZER_CONTRACT_PATH.read_bytes()),
                "training_config": resume_config,
            }
            temporary = checkpoint_dir / "latest.pt.tmp"
            torch.save(trainer_state, temporary)
            os.replace(temporary, checkpoint_dir / "latest.pt")
            print(json.dumps({"event": "checkpoint_saved", "epoch": epoch + 1, "path": str(checkpoint_dir / "latest.pt"), "resumable": True}))
        if distributed:
            import torch.distributed as dist
            dist.barrier()

    if best_state is None:
        print("ERROR: no training epochs ran; use --resume-from with --epochs greater than the saved epoch.", file=sys.stderr)
        return 2
    model_for_state = model.module if hasattr(model, "module") else model
    model_for_state.load_state_dict(best_state)

    # The held-out test split is evaluated exactly once, after checkpoint selection.
    # It is never used for gradients, early stopping, or selecting the best checkpoint.
    model.eval()
    test_losses = []
    with torch.no_grad():
        for xx, yy in batches(test_ids, False):
            with autocast_context():
                test_loss_batch = F.cross_entropy(model(xx).reshape(-1, VOCAB_SIZE), yy.reshape(-1))
            test_losses.append(float(test_loss_batch.cpu()))
    if not test_losses:
        raise RuntimeError("No independent-test batches; increase test corpus or reduce sequence length")
    independent_test_loss = sum(test_losses) / len(test_losses)

    model_for_export = model.module if hasattr(model, "module") else model
    tensors: dict[str, Any] = {
        "token_embedding.weight": model_for_export.token_embedding.weight,
        "final_norm.weight": model_for_export.final_norm.unsqueeze(0),
        "lm_head.weight": model_for_export.lm_head,
    }
    for i, layer in enumerate(model_for_export.layers):
        prefix = f"layers.{i}."
        for name in ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"):
            tensors[prefix + name + ".weight"] = getattr(layer, name)
        tensors[prefix + "input_norm.weight"] = layer.input_norm.unsqueeze(0)
        tensors[prefix + "post_attention_norm.weight"] = layer.post_attention_norm.unsqueeze(0)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if rank != 0:
        if distributed:
            import torch.distributed as dist
            dist.barrier()
            dist.destroy_process_group()
        return 0
    checkpoint_path = args.output_dir / "mkaos-owned.mkaosw"
    checkpoint_hash = write_mkaos_checkpoint(checkpoint_path, tensors)
    tokenizer_bytes = TOKENIZER_CONTRACT_PATH.read_bytes()
    tokenizer_payload = json.loads(tokenizer_bytes.decode("utf-8"))
    if tokenizer_payload["vocab_size"] != VOCAB_SIZE or tokenizer_payload["eos_id"] != 256:
        raise RuntimeError("Shared tokenizer contract changed during training; refusing export")
    tokenizer_path = args.output_dir / "tokenizer.json"
    tokenizer_path.write_bytes(tokenizer_bytes)
    report = {
        "format_version": 1,
        "model_id": "MKAOS-TR-FromScratch-Experimental",
        "training_mode": "experimental_local_only" if args.experimental_local_only else "source_approved",
        "redistribution_allowed": not args.experimental_local_only,
        "trained_from_random_initialization": True,
        "pretrained_model_used": None,
        "external_model_weights_used": False,
        "architecture": {"type": "MKAOS-GQA-SwiGLU", "vocab_size": VOCAB_SIZE, "hidden_size": d, "layers": args.layers, "query_heads": nh, "kv_heads": nkh, "intermediate_size": intermediate, "max_sequence_len": args.sequence_length},
        "tokenizer_sha256": sha256(tokenizer_bytes),
        "checkpoint_file": checkpoint_path.name,
        "checkpoint_sha256": checkpoint_hash,
        "dataset_id": manifest.get("dataset_id"),
        "dataset_revision": manifest.get("revision"),
        "manifest_sha256": manifest_file_sha256,
        "corpus_sha256": corpus_file_sha256,
        "seed": args.seed,
        "device": str(device),
        "backend_runtime": backend_runtime,
        "device_name": device_name,
        "precision": precision,
        "parameter_count": parameter_count,
        "estimated_training_memory_bytes": estimated_memory_bytes,
        "available_memory_bytes_before_model": available_memory_bytes or None,
        "hardware_runtime_probe": hardware_runtime_probe,
        "training_config": {
            "optimizer": "ZeroRedundancyOptimizer(AdamW)" if args.optimizer_state_sharding else "AdamW",
            "distributed_world_size": world_size,
            "distributed_data_parallel": distributed,
            "optimizer_state_sharding": args.optimizer_state_sharding,
            "gradient_checkpointing": args.gradient_checkpointing,
            "resume_from": str(args.resume_from) if args.resume_from else None,
            "initial_learning_rate": args.learning_rate,
            "schedule": "linear-warmup-then-cosine-decay",
            "warmup_steps": args.warmup_steps,
            "min_learning_rate_ratio": args.min_learning_rate_ratio,
            "micro_batch_size": args.batch_size,
            "gradient_accumulation_steps": args.gradient_accumulation_steps,
            "effective_batch_size": args.batch_size * args.gradient_accumulation_steps,
            "total_optimizer_steps": total_optimizer_steps,
            "gradient_clipping_max_norm": 1.0,
        },
        "split_sample_counts": {name: len(values) for name, values in splits.items()},
        "split_utf8_bytes": {name: sum(len(value.encode("utf-8")) for value in values) for name, values in splits.items()},
        "best_validation_loss": best_val,
        "independent_test_loss": independent_test_loss,
        "independent_test_evaluated_after_checkpoint_selection": True,
        "test_used_for_training_or_model_selection": False,
        "history": history,
        "warning": "Experimental from-scratch checkpoint. Test loss is a byte-level next-token metric, not proof of Turkish task competence. Training completion does not certify useful Turkish capability; independent human evaluation remains required."
    }
    report_path = args.output_dir / "training-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported MKAOS-native checkpoint: {checkpoint_path}")
    print(f"SHA-256: {checkpoint_hash}")
    print("WARNING: this is a from-scratch experimental model, not a validated production assistant.")
    if distributed:
        import torch.distributed as dist
        dist.barrier()
        dist.destroy_process_group()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

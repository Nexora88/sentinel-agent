#!/usr/bin/env python3
"""Train an original MKAOS decoder from random initialization; never downloads a model.

Corpus format: JSONL, one object per line: {"sample_id":"...", "text":"..."}.
A separately human-approved provenance manifest assigns each sample to a split.
The manifest's SHA-256 must match the UTF-8 bytes of each text field exactly.
Requires PyTorch only for training; no hub client, pretrained weights, or remote API.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import struct
import sys
from pathlib import Path
from typing import Any

MAGIC = b"MKAOSW1\0"
VOCAB_SIZE = 257  # UTF-8 bytes 0..255 plus EOS=256


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def encode_documents(texts: list[str]) -> list[int]:
    # Separator/EOS between documents prevents accidental concatenation semantics.
    ids: list[int] = []
    for text in texts:
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, type=Path, help="Approved local JSONL text corpus")
    parser.add_argument("--manifest", required=True, type=Path, help="Human-reviewed provenance manifest")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--sequence-length", type=int, default=128)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--kv-heads", type=int, default=2)
    parser.add_argument("--intermediate-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--seed", type=int, default=20261016)
    args = parser.parse_args()

    if min(args.epochs, args.batch_size, args.sequence_length, args.hidden_size,
           args.layers, args.heads, args.kv_heads, args.intermediate_size) < 1:
        parser.error("sizes, epochs and batch size must be positive")
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
        manifest_messages = validate_manifest(manifest)
        errors = [m for m in manifest_messages if not m.startswith("Metadata checks passed")]
        if errors:
            raise ValueError("Manifest validation failed:\n- " + "\n- ".join(errors))
        corpus = read_corpus(args.corpus)
        splits = validate_corpus_against_manifest(corpus, manifest)
    except (OSError, json.JSONDecodeError, ValueError, ImportError) as exc:
        print(f"ERROR: training data gate failed: {exc}", file=sys.stderr)
        return 2

    train_ids = encode_documents(splits["train"])
    val_ids = encode_documents(splits["validation"])
    if len(train_ids) < args.sequence_length + 1 or len(val_ids) < args.sequence_length + 1:
        print("ERROR: train and validation data each need at least sequence-length + 1 byte tokens", file=sys.stderr)
        return 2

    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
    except ImportError:
        print("ERROR: PyTorch is required for training. Install a locally approved PyTorch build; no model downloads are used.", file=sys.stderr)
        return 2

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    d, nh, nkh = args.hidden_size, args.heads, args.kv_heads
    hd, kv_width = d // nh, d // nh * nkh
    intermediate = args.intermediate_size

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
            # x: [batch, heads, seq, head_dim], Llama-style interleaved pairs.
            length = x.shape[-2]
            half = x.shape[-1] // 2
            positions = torch.arange(length, device=x.device, dtype=x.dtype)
            inv = 1.0 / (10000.0 ** (torch.arange(0, x.shape[-1], 2, device=x.device, dtype=x.dtype) / x.shape[-1]))
            angles = torch.outer(positions, inv)
            cos, sin = angles.cos()[None, None, :, :], angles.sin()[None, None, :, :]
            even, odd = x[..., 0::2], x[..., 1::2]
            return torch.stack((even * cos - odd * sin, even * sin + odd * cos), dim=-1).flatten(-2)

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
            scores = (q @ k.transpose(-2, -1)) / math.sqrt(hd)
            causal = torch.triu(torch.ones(length, length, device=x.device, dtype=torch.bool), diagonal=1)
            scores = scores.masked_fill(causal, float("-inf"))
            attended = (scores.softmax(dim=-1) @ v).transpose(1, 2).contiguous().view(b, length, d)
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
                x = layer(x)
            x = x * torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + 1e-5) * self.final_norm
            return x @ self.lm_head

    def batches(ids: list[int], shuffle: bool):
        starts = list(range(0, len(ids) - args.sequence_length, args.sequence_length))
        if shuffle:
            random.shuffle(starts)
        for offset in range(0, len(starts), args.batch_size):
            chunk = starts[offset:offset + args.batch_size]
            if not chunk:
                continue
            xx = torch.tensor([ids[s:s + args.sequence_length] for s in chunk], dtype=torch.long, device=device)
            yy = torch.tensor([ids[s + 1:s + args.sequence_length + 1] for s in chunk], dtype=torch.long, device=device)
            yield xx, yy

    model = MkaosFromScratch().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    best_val = float("inf")
    best_state = None
    history = []
    for epoch in range(args.epochs):
        model.train()
        train_losses = []
        for xx, yy in batches(train_ids, True):
            optimizer.zero_grad(set_to_none=True)
            loss = F.cross_entropy(model(xx).reshape(-1, VOCAB_SIZE), yy.reshape(-1))
            if not torch.isfinite(loss):
                raise RuntimeError("Non-finite training loss; aborting without checkpoint export")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_losses.append(float(loss.detach().cpu()))
        model.eval()
        val_losses = []
        with torch.no_grad():
            for xx, yy in batches(val_ids, False):
                val_losses.append(float(F.cross_entropy(model(xx).reshape(-1, VOCAB_SIZE), yy.reshape(-1)).cpu()))
        if not train_losses or not val_losses:
            raise RuntimeError("No train/validation batches; increase corpus size or reduce sequence length")
        val_loss = sum(val_losses) / len(val_losses)
        history.append({"epoch": epoch + 1, "train_loss": sum(train_losses) / len(train_losses), "validation_loss": val_loss})
        print(json.dumps(history[-1], ensure_ascii=False))
        if val_loss < best_val:
            best_val = val_loss
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}

    assert best_state is not None
    model.load_state_dict(best_state)
    tensors: dict[str, Any] = {
        "token_embedding.weight": model.token_embedding.weight,
        "final_norm.weight": model.final_norm.unsqueeze(0),
        "lm_head.weight": model.lm_head,
    }
    for i, layer in enumerate(model.layers):
        prefix = f"layers.{i}."
        for name in ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"):
            tensors[prefix + name + ".weight"] = getattr(layer, name)
        tensors[prefix + "input_norm.weight"] = layer.input_norm.unsqueeze(0)
        tensors[prefix + "post_attention_norm.weight"] = layer.post_attention_norm.unsqueeze(0)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "mkaos-owned.mkaosw"
    checkpoint_hash = write_mkaos_checkpoint(checkpoint_path, tensors)
    tokenizer_payload = {"format": "mkaos-byte-v1", "vocab_size": VOCAB_SIZE, "eos_id": 256, "mapping": "UTF-8 byte value -> same token ID; 256 is EOS"}
    tokenizer_bytes = (json.dumps(tokenizer_payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    tokenizer_path = args.output_dir / "tokenizer.json"
    tokenizer_path.write_bytes(tokenizer_bytes)
    report = {
        "format_version": 1,
        "model_id": "MKAOS-TR-FromScratch-Experimental",
        "trained_from_random_initialization": True,
        "pretrained_model_used": None,
        "external_model_weights_used": False,
        "architecture": {"type": "MKAOS-GQA-SwiGLU", "vocab_size": VOCAB_SIZE, "hidden_size": d, "layers": args.layers, "query_heads": nh, "kv_heads": nkh, "intermediate_size": intermediate, "max_sequence_len": args.sequence_length},
        "tokenizer_sha256": sha256(tokenizer_bytes),
        "checkpoint_file": checkpoint_path.name,
        "checkpoint_sha256": checkpoint_hash,
        "dataset_id": manifest.get("dataset_id"),
        "dataset_revision": manifest.get("revision"),
        "manifest_sha256": sha256(args.manifest.read_bytes()),
        "seed": args.seed,
        "device": str(device),
        "best_validation_loss": best_val,
        "history": history,
        "warning": "Experimental from-scratch checkpoint. Training completion does not certify useful Turkish capability. The held-out test split was not used for optimization or model selection."
    }
    report_path = args.output_dir / "training-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported MKAOS-native checkpoint: {checkpoint_path}")
    print(f"SHA-256: {checkpoint_hash}")
    print("WARNING: this is a from-scratch experimental model, not a validated production assistant.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

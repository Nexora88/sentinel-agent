#!/usr/bin/env python3
"""Train a small, project-owned byte-level MKAOS language-model prototype offline.

This is a research training loop, not a claim of competitive general intelligence or
production Rust-checkpoint compatibility. It uses only the supplied audited manifest;
it never downloads weights/data and never trains on the held-out test split.
PyTorch is an optional development dependency and is not added to runtime requirements.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "mkaos-byte-lm-v1"
BYTE_VOCAB_SIZE = 256
ALLOWED_LICENSES = {"CC0-1.0", "CC-BY-4.0", "MIT", "Apache-2.0"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_governed_manifest(path: Path, min_records_per_split: int = 1) -> tuple[dict[str, Any], dict[str, list[str]]]:
    """Fail closed unless the audited dataset manifest has all three source-level splits."""
    raw = path.read_bytes()
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("manifest must be valid UTF-8 JSON") from exc
    if not isinstance(manifest, dict) or manifest.get("training_allowed") is not True:
        raise ValueError("manifest is not explicitly approved for training")
    records = manifest.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("manifest has no records")
    split_text: dict[str, list[str]] = {"train": [], "validation": [], "test": []}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"record {index} must be an object")
        if record.get("split") not in split_text:
            raise ValueError(f"record {index} has an invalid split")
        for field in ("prompt", "response", "source_id", "source_uri", "license_id", "content_sha256"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                raise ValueError(f"record {index} missing {field}")
        if record.get("license_id") not in ALLOWED_LICENSES:
            raise ValueError(f"record {index} has a non-allowlisted license")
        if not record["source_uri"].startswith(("https://", "file://", "dataset://")):
            raise ValueError(f"record {index} has an unauditable source URI")
        if record.get("consent") is not True:
            raise ValueError(f"record {index} lacks explicit permission/consent")
        if record.get("review_status", "approved") != "approved":
            raise ValueError(f"record {index} has not passed human review")
        if record.get("personal_data") is True or record.get("sensitive_data") is True:
            raise ValueError(f"record {index} is marked as personal/sensitive")
        split_text[record["split"]].append(
            "Kullanıcı: " + record["prompt"].strip() + "\nMKAOS: " + record["response"].strip() + "\n"
        )
    too_small = {key: len(value) for key, value in split_text.items() if len(value) < min_records_per_split}
    if too_small:
        raise ValueError(f"split minimum not met: {too_small}")
    # One source may only belong to one split; this is a leakage guard.
    source_splits: dict[str, set[str]] = {}
    for record in records:
        source_splits.setdefault(record["source_id"], set()).add(record["split"])
    leaked = [source for source, splits in source_splits.items() if len(splits) > 1]
    if leaked:
        raise ValueError(f"source leakage across splits: {len(leaked)} source(s)")
    return manifest, split_text


def encode_stream(texts: list[str]) -> bytes:
    # Project-owned, deterministic UTF-8 byte tokenizer. Vocabulary IDs are byte values 0..255.
    return b"\n".join(text.encode("utf-8") for text in texts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path, help="audited JSON manifest from prepare_mkaos_training_dataset.py")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--context-length", type=int, default=128)
    parser.add_argument("--width", type=int, default=128)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--seed", type=int, default=20261015)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--min-records-per-split", type=int, default=2)
    args = parser.parse_args(argv)
    if min(args.steps, args.batch_size, args.context_length, args.width, args.layers, args.heads) < 1:
        parser.error("steps, batch-size, context-length, width, layers and heads must be positive")
    if args.width % args.heads:
        parser.error("width must be divisible by heads")
    if not 0 < args.learning_rate <= 0.1:
        parser.error("learning-rate must be in (0, 0.1]")
    try:
        manifest, split_text = load_governed_manifest(args.manifest, args.min_records_per_split)
    except (OSError, ValueError) as exc:
        print(f"Training blocked: {exc}", file=sys.stderr)
        return 2

    try:
        import torch
        from torch import nn
    except ImportError:
        print("Training requires optional PyTorch in the development environment; runtime requirements are unchanged.", file=sys.stderr)
        return 3

    if args.device == "cuda" and not torch.cuda.is_available():
        print("Training blocked: CUDA requested but unavailable.", file=sys.stderr)
        return 2
    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    train_bytes = encode_stream(split_text["train"])
    validation_bytes = encode_stream(split_text["validation"])
    if len(train_bytes) <= args.context_length + 1 or len(validation_bytes) <= args.context_length + 1:
        print("Training blocked: train and validation byte streams must each exceed context-length + 1.", file=sys.stderr)
        return 2

    class ByteCausalLM(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.token_embedding = nn.Embedding(BYTE_VOCAB_SIZE, args.width)
            self.position_embedding = nn.Embedding(args.context_length, args.width)
            layer = nn.TransformerEncoderLayer(
                d_model=args.width, nhead=args.heads, dim_feedforward=4 * args.width,
                dropout=0.0, batch_first=True, norm_first=True, activation="gelu",
            )
            self.blocks = nn.TransformerEncoder(layer, num_layers=args.layers, enable_nested_tensor=False)
            self.final_norm = nn.LayerNorm(args.width)
            self.lm_head = nn.Linear(args.width, BYTE_VOCAB_SIZE, bias=False)
            self.lm_head.weight = self.token_embedding.weight

        def forward(self, tokens):
            length = tokens.shape[1]
            positions = torch.arange(length, device=tokens.device)
            x = self.token_embedding(tokens) + self.position_embedding(positions)[None, :, :]
            mask = torch.triu(torch.ones(length, length, device=tokens.device, dtype=torch.bool), diagonal=1)
            x = self.blocks(x, mask=mask)
            return self.lm_head(self.final_norm(x))

    def batch_from(stream: bytes, batch_size: int):
        max_start = len(stream) - args.context_length - 1
        starts = torch.randint(0, max_start + 1, (batch_size,))
        xs = torch.stack([torch.tensor(list(stream[int(s):int(s) + args.context_length]), dtype=torch.long) for s in starts])
        ys = torch.stack([torch.tensor(list(stream[int(s) + 1:int(s) + args.context_length + 1]), dtype=torch.long) for s in starts])
        return xs.to(device), ys.to(device)

    model = ByteCausalLM().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    started = time.time()
    train_losses: list[float] = []
    validation_loss = None
    for step in range(1, args.steps + 1):
        model.train()
        x, y = batch_from(train_bytes, args.batch_size)
        logits = model(x)
        loss = nn.functional.cross_entropy(logits.reshape(-1, BYTE_VOCAB_SIZE), y.reshape(-1))
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        train_losses.append(float(loss.detach().cpu()))
        if step == 1 or step % max(1, args.steps // 10) == 0 or step == args.steps:
            model.eval()
            with torch.no_grad():
                vx, vy = batch_from(validation_bytes, min(args.batch_size, 8))
                validation_loss = float(nn.functional.cross_entropy(
                    model(vx).reshape(-1, BYTE_VOCAB_SIZE), vy.reshape(-1)
                ).cpu())
            print(json.dumps({"step": step, "train_loss": round(train_losses[-1], 5),
                              "validation_loss": round(validation_loss, 5)}, ensure_ascii=False))

    args.output_dir.mkdir(parents=True, exist_ok=False)
    checkpoint = args.output_dir / "mkaos-byte-lm.pt"
    torch.save({
        "schema_version": SCHEMA_VERSION,
        "config": {"vocab_size": BYTE_VOCAB_SIZE, "context_length": args.context_length,
                   "width": args.width, "layers": args.layers, "heads": args.heads},
        "state_dict": model.cpu().state_dict(),
    }, checkpoint)
    checkpoint_hash = sha256_bytes(checkpoint.read_bytes())
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "experimental_trained_checkpoint",
        "checkpoint_file": checkpoint.name,
        "checkpoint_sha256": checkpoint_hash,
        "dataset_manifest_sha256": sha256_bytes(args.manifest.read_bytes()),
        "dataset_content_sha256": manifest.get("summary", {}).get("content_sha256"),
        "split_counts": {key: len(value) for key, value in split_text.items()},
        "training_records_used": len(split_text["train"]),
        "validation_records_used": len(split_text["validation"]),
        "test_records_used_for_training": 0,
        "test_split_untouched": True,
        "tokenizer": {"kind": "project-owned-utf8-byte", "vocab_size": BYTE_VOCAB_SIZE},
        "architecture": {"kind": "project-owned-byte-causal-transformer", "width": args.width,
                         "layers": args.layers, "heads": args.heads, "context_length": args.context_length},
        "optimizer": "AdamW", "learning_rate": args.learning_rate, "seed": args.seed,
        "steps": args.steps, "batch_size": args.batch_size, "device": device,
        "train_loss_first": round(train_losses[0], 6),
        "train_loss_last": round(train_losses[-1], 6),
        "validation_loss_last": round(float(validation_loss), 6) if validation_loss is not None else None,
        "elapsed_seconds": round(time.time() - started, 3),
        "torch_version": torch.__version__,
        "production_ready": False,
        "rust_engine_compatible": False,
        "release_note": "Research prototype only; evaluate held-out test split and implement/verify matching Rust architecture before routing production traffic.",
    }
    (args.output_dir / "training-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

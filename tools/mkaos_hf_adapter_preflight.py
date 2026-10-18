#!/usr/bin/env python3
"""Read-only, dependency-free preflight for Hugging Face model directories.

This does NOT convert weights. MKAOSW1 is a distinct architecture/serialization
contract; renaming or concatenating safetensors cannot make an arbitrary HF
checkpoint compatible. The tool reads only local config/tokenizer/weight headers.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

MAX_HEADER_BYTES = 64 * 1024 * 1024
WEIGHT_SUFFIXES = (".safetensors",)


def inspect_safetensors(path: Path) -> dict:
    with path.open("rb") as f:
        raw_len = f.read(8)
        if len(raw_len) != 8:
            raise ValueError("file is shorter than a safetensors header prefix")
        header_len = struct.unpack("<Q", raw_len)[0]
        if header_len < 2 or header_len > MAX_HEADER_BYTES:
            raise ValueError(f"invalid or excessive header length: {header_len}")
        header = f.read(header_len)
        if len(header) != header_len:
            raise ValueError("truncated safetensors header")
    parsed = json.loads(header.decode("utf-8"))
    tensors = {}
    for name, meta in parsed.items():
        if name == "__metadata__":
            continue
        if not isinstance(meta, dict) or not isinstance(meta.get("shape"), list):
            raise ValueError(f"invalid tensor metadata for {name!r}")
        tensors[name] = {"dtype": meta.get("dtype"), "shape": meta["shape"]}
    return {"file": path.name, "header_bytes": header_len, "tensor_count": len(tensors),
            "tensors": tensors}


def inspect_model(model_dir: Path) -> dict:
    if not model_dir.is_dir():
        raise ValueError(f"model directory not found: {model_dir}")
    config_path = model_dir / "config.json"
    if not config_path.is_file():
        raise ValueError("config.json is missing")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    weight_files = sorted(p for p in model_dir.iterdir()
                          if p.is_file() and p.suffix in WEIGHT_SUFFIXES)
    if not weight_files:
        raise ValueError("no local .safetensors file found (shard indexes alone are insufficient)")
    reports = [inspect_safetensors(p) for p in weight_files]
    tokenizer_files = [name for name in ("tokenizer.json", "tokenizer.model",
                                          "tokenizer_config.json", "vocab.json",
                                          "merges.txt") if (model_dir / name).is_file()]
    license_files = [name for name in ("LICENSE", "LICENSE.txt", "NOTICE",
                                        "README.md", "LICENSE.md")
                     if (model_dir / name).is_file()]
    return {
        "model_dir": str(model_dir.resolve()),
        "model_type": config.get("model_type"),
        "architectures": config.get("architectures", []),
        "torch_dtype": config.get("torch_dtype"),
        "weight_files": reports,
        "tokenizer_files_present": tokenizer_files,
        "license_or_model_card_files_present": license_files,
        "conversion": {
            "status": "NOT_CONVERTED",
            "reason": "MKAOSW1 currently uses its own tensor layout and byte tokenizer; "
                      "generic HF safetensors are not drop-in compatible.",
        },
        "network_used": False,
        "files_modified": False,
        "license_approval": "NOT_ASSESSED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_dir", type=Path, help="existing local HF model directory")
    parser.add_argument("--output", type=Path, help="optional JSON report path")
    args = parser.parse_args()
    try:
        report = inspect_model(args.model_dir)
    except (OSError, ValueError, json.JSONDecodeError, UnicodeError, struct.error) as exc:
        report = {"status": "BLOCKED", "error": str(exc), "network_used": False,
                  "files_modified": False, "conversion": "NOT_PERFORMED"}
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Convert safetensors into MKAOSW1. This is format conversion, not architecture adaptation.

Requires: pip install safetensors torch
Preserves names/shapes and converts supported floating tensors to F32. It does not
transpose/rename parameters or guarantee the Rust runtime supports the architecture.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from safetensors import safe_open


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--manifest", type=Path)
    ap.add_argument("--max-elements", type=int, default=300_000_000)
    args = ap.parse_args()
    try:
        import torch
    except ImportError as exc:
        raise SystemExit("PyTorch is required for BF16/FP16 to F32 conversion: pip install torch") from exc

    tensors = []
    with safe_open(str(args.input), framework="pt", device="cpu") as f:
        for name in sorted(f.keys()):
            tensor = f.get_tensor(name).detach().contiguous()
            if tensor.ndim == 1:
                rows, cols = 1, tensor.shape[0]
            elif tensor.ndim == 2:
                rows, cols = tensor.shape
            else:
                raise SystemExit(f"unsupported tensor rank {tensor.ndim}: {name}; only rank 1/2 is supported")
            if rows == 0 or cols == 0 or rows * cols > args.max_elements:
                raise SystemExit(f"invalid/too-large tensor shape for {name}: {(rows, cols)}")
            if not tensor.is_floating_point():
                raise SystemExit(f"unsupported non-floating tensor dtype for {name}: {tensor.dtype}")
            values = tensor.to(dtype=torch.float32).reshape(-1).tolist()
            if any(not math.isfinite(v) for v in values):
                raise SystemExit(f"non-finite value in tensor: {name}")
            tensors.append((name, rows, cols, values))

    if not tensors:
        raise SystemExit("checkpoint contains no tensors")
    out = bytearray(b"MKAOSW1\0")
    out.extend(struct.pack("<I", len(tensors)))
    for name, rows, cols, values in tensors:
        encoded = name.encode("utf-8")
        if not encoded or len(encoded) > 256:
            raise SystemExit(f"tensor name length outside Rust loader limit: {name!r}")
        out.extend(struct.pack("<H", len(encoded)))
        out.extend(encoded)
        out.extend(struct.pack("<II", rows, cols))
        for value in values:
            out.extend(struct.pack("<f", value))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(out)
    report = {
        "format": "MKAOSW1",
        "source": str(args.input),
        "source_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "output": str(args.output),
        "output_sha256": hashlib.sha256(out).hexdigest(),
        "tensor_count": len(tensors),
        "tensors": [{"name": n, "shape": [r, c]} for n, r, c, _ in tensors],
        "warning": "Format conversion only; architecture mapping, transpose rules, tokenizer compatibility and Rust manifest validation are separate steps."
    }
    if args.manifest:
        args.manifest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "tensors"}, indent=2))


if __name__ == "__main__":
    main()

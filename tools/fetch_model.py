#!/usr/bin/env python3
"""Fetch only JSON/safetensors assets at an immutable Hugging Face revision and hash them."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

REPO = "HuggingFaceTB/SmolLM2-135M-Instruct"
REVISION = "12fd25f77366fa6b3b4b768ec3050bf629380bac"
FILES = ["README.md", "config.json", "model.safetensors",
         "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json"]
MAX_BYTES = {
    "README.md": 2_000_000, "config.json": 200_000,
    "model.safetensors": 600_000_000, "tokenizer.json": 10_000_000,
    "tokenizer_config.json": 200_000, "special_tokens_map.json": 200_000,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sums = []
    for name in FILES:
        url = f"https://huggingface.co/{REPO}/resolve/{REVISION}/{name}"
        request = Request(url, headers={"User-Agent": "MKAOS-model-audit/1.0"})
        with urlopen(request, timeout=60) as response:
            data = response.read(MAX_BYTES[name] + 1)
        if len(data) > MAX_BYTES[name]:
            raise SystemExit(f"Refusing oversized artifact: {name}")
        path = args.output_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        sums.append(f"{digest}  {name}")
        print(f"{digest}  {len(data)} bytes  {name}")
    (args.output_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    metadata = {
        "model_id": REPO, "revision": REVISION, "license": "Apache-2.0",
        "files": [{"path": line.split("  ", 1)[1], "sha256": line.split("  ", 1)[0]} for line in sums],
        "warning": "Verify LICENSE and model card before redistribution; hashes establish integrity only, not authorship or license."
    }
    (args.output_dir / "model-lock.generated.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

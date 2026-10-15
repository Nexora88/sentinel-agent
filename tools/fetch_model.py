#!/usr/bin/env python3
"""Fetch pinned, size-bounded Hugging Face artifacts and compute exact SHA-256 hashes."""
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


def fetch_one(name: str, output_dir: Path) -> dict:
    url = f"https://huggingface.co/{REPO}/resolve/{REVISION}/{name}"
    request = Request(url, headers={"User-Agent": "MKAOS-model-audit/1.1"})
    digest = hashlib.sha256()
    size = 0
    path = output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    # Stream to disk and stop immediately if the immutable artifact exceeds its cap.
    with urlopen(request, timeout=60) as response, path.open("wb") as target:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES[name]:
                target.close()
                path.unlink(missing_ok=True)
                raise SystemExit(f"Refusing oversized artifact: {name} > {MAX_BYTES[name]} bytes")
            digest.update(chunk)
            target.write(chunk)
    sha256 = digest.hexdigest()
    print(f"{sha256}  {size} bytes  {name}")
    return {"path": name, "url": url, "bytes": size, "sha256": sha256}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--lock-file", type=Path, help="Optional model-lock.json to update after successful verification")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = [fetch_one(name, args.output_dir) for name in FILES]
    (args.output_dir / "SHA256SUMS").write_text(
        "".join(f"{item['sha256']}  {item['path']}\n" for item in records), encoding="utf-8")
    metadata = {
        "model_id": REPO, "revision": REVISION, "license": "Apache-2.0",
        "files": records,
        "warning": "Hashes establish byte integrity only. Confirm the pinned model-card license declaration and applicable license text before redistribution."
    }
    (args.output_dir / "model-lock.generated.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    if args.lock_file:
        lock = json.loads(args.lock_file.read_text(encoding="utf-8"))
        if lock.get("model_id") != REPO or lock.get("revision") != REVISION:
            raise SystemExit("Lock model ID/revision does not match the downloader's immutable pin")
        by_path = {item["path"]: item["sha256"] for item in records}
        lock["weights"]["sha256"] = by_path["model.safetensors"]
        lock["weights"]["sha256_status"] = "measured_from_pinned_artifact"
        for item in lock["tokenizer"]["files"]:
            item["sha256"] = by_path.get(item["path"])
        lock["tokenizer"]["sha256_status"] = "measured_from_pinned_artifacts"
        args.lock_file.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
        print(f"Updated verified hashes in {args.lock_file}")


if __name__ == "__main__":
    main()

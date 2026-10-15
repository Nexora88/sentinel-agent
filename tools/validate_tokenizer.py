#!/usr/bin/env python3
"""Cross-check MKAOS's Rust tokenizer adapter against Hugging Face Python artifacts.

Requires: pip install tokenizers transformers
Run after tools/fetch_model.py:
  python tools/validate_tokenizer.py --model-dir models/smollm2-135m-instruct
The test intentionally fails if the exact chat template cannot be evaluated locally.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

SAMPLES = [
    "Hello, world!",
    "The quick brown fox jumps over 13 lazy dogs.",
    "Merhaba dünya! Nasılsın? İstanbul, Edirne ve Tekirdağ.",
    "Türkçe karakterler: ğüşiöç ĞÜŞİÖÇ; sayılar 12345.",
    "<|im_start|>",
    "<|im_end|>",
    "<|im_sep|>",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    args = parser.parse_args()
    model_dir = args.model_dir
    tokenizer_json = model_dir / "tokenizer.json"
    tokenizer_config = model_dir / "tokenizer_config.json"
    if not tokenizer_json.is_file() or not tokenizer_config.is_file():
        raise SystemExit("Missing tokenizer.json/tokenizer_config.json; fetch pinned artifacts first.")
    try:
        from tokenizers import Tokenizer
        from transformers import AutoTokenizer
    except ImportError as exc:
        raise SystemExit("Install validation dependencies: pip install tokenizers transformers") from exc

    rust_manifest = Path("engine/mkaos-hf-adapter/Cargo.toml")
    probe = subprocess.run(
        ["cargo", "run", "--quiet", "--manifest-path", str(rust_manifest),
         "--bin", "tokenizer_probe", "--", str(tokenizer_json), *SAMPLES],
        check=True, capture_output=True, text=True,
    )
    rust_lines = probe.stdout.splitlines()
    if len(rust_lines) != len(SAMPLES):
        raise SystemExit(f"Rust probe returned {len(rust_lines)} rows for {len(SAMPLES)} samples")
    reference = Tokenizer.from_file(str(tokenizer_json))
    for sample, line in zip(SAMPLES, rust_lines):
        rust_ids = [int(item) for item in line.split(",") if item]
        hf_ids = reference.encode(sample, add_special_tokens=False).ids
        if rust_ids != hf_ids:
            raise SystemExit(f"ID mismatch for {sample!r}: Rust={rust_ids}, HF={hf_ids}")
        print(f"PASS token IDs: {sample!r} -> {rust_ids}")

    # Verify every declared special token resolves as a single dedicated token.
    config = json.loads(tokenizer_config.read_text(encoding="utf-8"))
    special_values = []
    for key in ("bos_token", "eos_token", "unk_token", "pad_token"):
        value = config.get(key)
        if isinstance(value, str):
            special_values.append(value)
        elif isinstance(value, dict) and isinstance(value.get("content"), str):
            special_values.append(value["content"])
    special_values += ["<|im_start|>", "<|im_end|>", "<|im_sep|>"]
    for token in dict.fromkeys(special_values):
        ids = reference.encode(token, add_special_tokens=False).ids
        if len(ids) != 1:
            raise SystemExit(f"Special token is not one ID: {token!r} -> {ids}")
        print(f"PASS special token: {token!r} -> {ids[0]}")

    rust_template = subprocess.run(
        ["cargo", "run", "--quiet", "--manifest-path", str(rust_manifest),
         "--bin", "tokenizer_probe", "--", str(tokenizer_json), "--chat-template"],
        check=True, capture_output=True, text=True,
    ).stdout
    hf_tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    messages = [
        {"role": "system", "content": "Answer briefly and accurately."},
        {"role": "user", "content": "Merhaba, how are you?"},
    ]
    try:
        hf_template = hf_tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    except Exception as exc:
        raise SystemExit(f"Could not evaluate pinned HF chat template: {exc}") from exc
    if rust_template != hf_template:
        print("RUST CHAT TEMPLATE:", repr(rust_template), file=sys.stderr)
        print("HF CHAT TEMPLATE:  ", repr(hf_template), file=sys.stderr)
        raise SystemExit("Chat-template mismatch; do not mark tokenizer integration compatible.")
    print("PASS chat template: Rust rendering matches Hugging Face apply_chat_template output")
    print(f"PASS: {len(SAMPLES)} multilingual/token-special text cases; {len(set(special_values))} special-token spellings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

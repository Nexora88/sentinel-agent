#!/usr/bin/env python3
"""Compare MKAOS final-position logits with the local Hugging Face reference model.

Requires downloaded pinned artifacts and: pip install torch transformers tokenizers
This is a real compatibility gate; it deliberately does not synthesize weights or pass
when the model files are absent.
"""
import argparse
import json
import subprocess
from pathlib import Path

PROMPTS = [
    "Hello. Answer with one short sentence.",
    "Merhaba. Bir cümleyle Türkiye'nin başkentini söyle.",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--max-abs-error", type=float, default=0.03)
    parser.add_argument("--min-cosine", type=float, default=0.999)
    args = parser.parse_args()
    model_dir = args.model_dir
    config_path = model_dir / "config.json"
    weights_path = model_dir / "model.safetensors"
    if not config_path.is_file() or not weights_path.is_file():
        raise SystemExit("Missing pinned config.json/model.safetensors; no synthetic fallback is allowed.")
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise SystemExit("Install reference dependencies: pip install torch transformers tokenizers") from exc

    reference_tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    reference_model = AutoModelForCausalLM.from_pretrained(
        str(model_dir), local_files_only=True, torch_dtype=torch.float32,
        low_cpu_mem_usage=True,
    ).cpu().eval()
    for prompt in PROMPTS:
        encoded = reference_tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
        ids = encoded["input_ids"][0].tolist()
        with torch.inference_mode():
            expected = reference_model(**encoded).logits[0, -1].cpu().float()
        command = [
            "cargo", "run", "--release", "--quiet",
            "--manifest-path", "engine/mkaos-hf-adapter/Cargo.toml",
            "--bin", "mkaos_logits", "--", str(config_path), str(weights_path),
            ",".join(map(str, ids)),
        ]
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
        actual = torch.tensor(json.loads(completed.stdout), dtype=torch.float32)
        if actual.shape != expected.shape:
            raise SystemExit(f"Logit shape mismatch for {prompt!r}: MKAOS={tuple(actual.shape)}, HF={tuple(expected.shape)}")
        max_abs = torch.max(torch.abs(actual - expected)).item()
        cosine = torch.nn.functional.cosine_similarity(actual, expected, dim=0).item()
        ref_top = int(torch.argmax(expected).item())
        mkaos_top = int(torch.argmax(actual).item())
        print(json.dumps({
            "prompt": prompt, "input_token_ids": ids,
            "vocab_size": int(expected.numel()), "max_abs_error": max_abs,
            "cosine_similarity": cosine, "hf_top_token": ref_top,
            "mkaos_top_token": mkaos_top, "top_token_match": ref_top == mkaos_top,
        }, ensure_ascii=False))
        if max_abs > args.max_abs_error or cosine < args.min_cosine or ref_top != mkaos_top:
            raise SystemExit("FAIL: MKAOS logits diverge from the Hugging Face reference.")
    print("PASS: all real-model logits checks met the configured thresholds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

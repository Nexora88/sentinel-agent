#!/usr/bin/env python3
"""Download a pinned public model in CI, verify hashes, then generate offline."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import threading
import time
from pathlib import Path

import psutil
import torch
from huggingface_hub import hf_hub_download
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

MODEL_ID = "HuggingFaceTB/SmolLM2-135M-Instruct"
REVISION = "12fd25f77366fa6b3b4b768ec3050bf629380bac"
EXPECTED = {
    "model.safetensors": "5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c",
    "tokenizer.json": "9ca9acddb6525a194ec8ac7a87f24fbba7232a9a15ffa1af0c1224fcd888e47c",
    "tokenizer_config.json": "4ec77d44f62efeb38d7e044a1db318f6a939438425312dfa333b8382dbad98df",
    "special_tokens_map.json": "2b7379f3ae813529281a5c602bc5a11c1d4e0a99107aaa597fe936c1e813ca52",
}
ROOT = Path("artifacts/offline-smollm2")
ROOT.mkdir(parents=True, exist_ok=True)
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

# Network is used only to obtain artifacts at the immutable revision.
downloaded = {}
for filename, expected_hash in EXPECTED.items():
    path = Path(hf_hub_download(
        repo_id=MODEL_ID, filename=filename, revision=REVISION,
        local_dir=str(ROOT), local_dir_use_symlinks=False,
    ))
    actual_hash = sha256(path)
    if actual_hash != expected_hash:
        raise RuntimeError(f"SHA-256 mismatch for {filename}: {actual_hash}")
    downloaded[filename] = {"sha256": actual_hash, "bytes": path.stat().st_size}

for filename in ("config.json", "generation_config.json"):
    try:
        path = Path(hf_hub_download(
            repo_id=MODEL_ID, filename=filename, revision=REVISION,
            local_dir=str(ROOT), local_dir_use_symlinks=False,
        ))
        downloaded[filename] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    except Exception:
        if filename == "config.json":
            raise

# From this point, prohibit Hub access and load only the downloaded local files.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
tokenizer = AutoTokenizer.from_pretrained(ROOT, local_files_only=True)
model = AutoModelForCausalLM.from_pretrained(
    ROOT, local_files_only=True, use_safetensors=True,
    torch_dtype=torch.float32, low_cpu_mem_usage=True,
)
model.eval()
if model.config.model_type != "llama":
    raise RuntimeError(f"Unexpected model architecture: {model.config.model_type}")

prompt = "Türkiye'nin başkenti neresidir? Kısa ve doğru cevap ver."
messages = [{"role": "user", "content": prompt}]
if getattr(tokenizer, "chat_template", None):
    rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
else:
    # SmolLM2-Instruct uses ChatML-style role markers; a raw plain-text prompt
    # can cause the model to echo the final instruction instead of answering.
    rendered = (
        "<|im_start|>system\\nYou are a helpful assistant. Answer the user's question directly and briefly.\\n<|im_end|>\\n"
        f"<|im_start|>user\\n{prompt}\\n<|im_end|>\\n<|im_start|>assistant\\n"
    )
inputs = tokenizer(rendered, return_tensors="pt")
process = psutil.Process()
baseline_rss = process.memory_info().rss
runs = []

def generate_once(index: int) -> dict:
    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True, timeout=180)
    kwargs = dict(**inputs, streamer=streamer, max_new_tokens=48, do_sample=False,
                  use_cache=True, pad_token_id=tokenizer.eos_token_id)
    started = time.perf_counter()
    worker = threading.Thread(target=model.generate, kwargs=kwargs, daemon=True)
    worker.start()
    first_token_time = None
    chunks = []
    for chunk in streamer:
        if chunk and first_token_time is None:
            first_token_time = time.perf_counter()
        chunks.append(chunk)
    worker.join(timeout=180)
    if worker.is_alive():
        raise TimeoutError("generation did not finish in 180 seconds")
    finished = time.perf_counter()
    text = "".join(chunks).strip()
    if not text:
        raise RuntimeError("offline model produced an empty answer")
    if "ankara" not in text.casefold():
        raise RuntimeError(
            "Turkish factual acceptance test failed: expected the answer to mention Ankara; "
            f"received {text!r}"
        )
    token_count = len(tokenizer.encode(text, add_special_tokens=False))
    if token_count <= 0:
        raise RuntimeError("generated answer token count is zero")
    return {
        "run": index,
        "answer": text,
        "generated_tokens_estimate": token_count,
        "ttft_ms": round(((first_token_time or finished) - started) * 1000, 2),
        "total_generation_ms": round((finished - started) * 1000, 2),
        "tokens_per_second_estimate": round(token_count / max(finished - started, 1e-9), 3),
        "process_rss_after_run_mb": round(process.memory_info().rss / (1024 * 1024), 2),
    }

# First run is cold-start; report it separately and do not hide it in the average.
for i in range(1, 4):
    runs.append(generate_once(i))

report = {
    "status": "passed",
    "model_id": MODEL_ID,
    "revision": REVISION,
    "license": "Apache-2.0 (pinned model card)",
    "architecture": model.__class__.__name__,
    "tokenizer_class": tokenizer.__class__.__name__,
    "offline_inference": True,
    "offline_env": {"HF_HUB_OFFLINE": os.environ["HF_HUB_OFFLINE"],
                    "TRANSFORMERS_OFFLINE": os.environ["TRANSFORMERS_OFFLINE"],
                    "local_files_only": True},
    "integrity": downloaded,
    "prompt": prompt,
    "runs": runs,
    "ttft_ms_mean": round(sum(r["ttft_ms"] for r in runs) / len(runs), 2),
    "tokens_per_second_estimate_mean": round(sum(r["tokens_per_second_estimate"] for r in runs) / len(runs), 3),
    "process_rss_baseline_mb": round(baseline_rss / (1024 * 1024), 2),
    "process_rss_max_sampled_mb": max(r["process_rss_after_run_mb"] for r in runs),
    "memory_metric_note": "RSS sampled after each generation; this is not a high-frequency peak-RSS measurement.",
    "torch_version": torch.__version__,
    "python_version": platform.python_version(),
    "runner_note": "GitHub-hosted CI runner, CPU float32; these timings are not the user's Windows PC measurements.",
}
Path("offline-model-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))

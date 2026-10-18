#!/usr/bin/env python3
"""CPU-only HF reference smoke test; saves logits for future cross-runtime parity."""
from __future__ import annotations
import argparse, hashlib, json, platform, time
from pathlib import Path

MODEL_ID = "HuggingFaceTB/SmolLM2-135M-Instruct"
MODEL_REVISION = "12fd25f77366fa6b3b4b768ec3050bf629380bac"
MODEL_LICENSE_METADATA = "apache-2.0"
INPUT_TEXT = "Explain what a computer program is in one sentence."

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="JSON metrics report")
    parser.add_argument("--logits-output", type=Path, default=Path("artifacts/mkaos-hf-reference-logits.npz"),
                        help="compressed reference logits and token inputs (.npz)")
    args = parser.parse_args()
    import numpy as np
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.set_num_threads(min(4, torch.get_num_threads()))
    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, revision=MODEL_REVISION, torch_dtype=torch.float32,
    ).to("cpu").eval()
    load_seconds = time.perf_counter() - started
    inputs = tokenizer(INPUT_TEXT, return_tensors="pt")
    with torch.inference_mode():
        t0 = time.perf_counter()
        first = model(**inputs).logits.detach().to(torch.float32).cpu().contiguous()
        first_seconds = time.perf_counter() - t0
        second = model(**inputs).logits.detach().to(torch.float32).cpu().contiguous()
    delta = (first - second).abs()
    max_abs = float(delta.max().item())
    # Floating-point cosine implementations can round slightly above 1.0 for identical vectors.
    cosine_raw = float(torch.nn.functional.cosine_similarity(first.reshape(1, -1), second.reshape(1, -1)).item())
    cosine = max(-1.0, min(1.0, cosine_raw))
    logits_np = first.numpy()
    input_ids_np = inputs["input_ids"].cpu().numpy()
    attention_mask_np = inputs.get("attention_mask", torch.ones_like(inputs["input_ids"])).cpu().numpy()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.logits_output.parent.mkdir(parents=True, exist_ok=True)
    # The .npz is intended as a reproducible reference fixture for a future adapter;
    # it does not itself establish Rust/MKAOSW1 compatibility.
    np.savez_compressed(
        args.logits_output,
        logits=logits_np,
        input_ids=input_ids_np,
        attention_mask=attention_mask_np,
        input_text=np.asarray(INPUT_TEXT),
        model_id=np.asarray(MODEL_ID),
        model_revision=np.asarray(MODEL_REVISION),
    )
    logits_bytes = logits_np.tobytes(order="C")
    report = {
        "test": "hf_cpu_reference_smoke_not_conversion",
        "model_id": MODEL_ID, "revision": MODEL_REVISION,
        "license_metadata": MODEL_LICENSE_METADATA,
        "architecture": model.config.architectures, "model_type": model.config.model_type,
        "parameter_count": sum(p.numel() for p in model.parameters()),
        "device": "cpu", "platform": platform.platform(), "python": platform.python_version(),
        "torch": torch.__version__, "transformers": transformers.__version__,
        "input_text": INPUT_TEXT, "input_token_count": int(inputs["input_ids"].shape[-1]),
        "input_ids": input_ids_np.tolist(), "logit_shape": list(first.shape),
        "load_seconds": round(load_seconds, 4), "forward_seconds": round(first_seconds, 4),
        "repeat_forward_max_absolute_error": max_abs,
        "repeat_forward_cosine_similarity": cosine,
        "repeat_forward_passed": max_abs <= 1e-6 and abs(cosine - 1.0) <= 1e-6,
        "reference_logits_sha256": hashlib.sha256(logits_bytes).hexdigest(),
        "reference_logits_file": str(args.logits_output),
        "reference_logits_file_sha256": hashlib.sha256(args.logits_output.read_bytes()).hexdigest(),
        "conversion_status": "NOT_PERFORMED", "mkaosw1_parity_status": "NOT_TESTED_NO_ADAPTER",
        "note": "Repeatability check only; not a quality evaluation or cross-runtime parity test.",
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["repeat_forward_passed"]:
        raise SystemExit("CPU reference repeatability check failed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

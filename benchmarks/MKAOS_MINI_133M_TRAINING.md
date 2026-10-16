# MKAOS-Mini 133M: training and evaluation milestone

**Status: profile and measurement tools are committed; a real corpus training run has not been executed.** The existing trainer intentionally fails closed unless the corpus, source registry, provenance manifest, human review, privacy clearance and machine-memory preflight pass.

## Why 133M first

The profile in `configs/mkaos/train-135m.json` defines a 133,194,752-parameter decoder using the current trainer architecture. CI computes this number from the actual dimensions instead of trusting a marketing label. This is a first training milestone inside the requested 100M–500M range, not a promise of high-quality general intelligence.

The model is initialized from random weights. It does not import SmolLM2, Qwen or another model's weights. The byte tokenizer is retained only to validate the current training/runtime contract; it is inefficient for Turkish and is not the final quality design. Before claiming strong Turkish understanding, the project needs a reviewed subword tokenizer, a compatible Rust implementation, and a measured comparison on held-out tasks.

FP32 weights alone are about 533 MB (507.9 MiB); this excludes runtime memory. Training uses additional memory for gradients, AdamW state and activations. The trainer estimates memory and blocks the run when its estimate exceeds 80% of detected available RAM/VRAM. Do not bypass that guard to force training onto an undersized machine.

## Prepare and launch

Use only a locally supplied corpus whose records exactly match the provenance manifest. The manifest must be human-reviewed and must clear the source-register, license, PII, split-leakage and SHA-256 checks. The profile runner does not download a dataset or weights.

```bash
python tools/train_mkaos_profile.py \
  --profile configs/mkaos/train-135m.json \
  --corpus /path/to/approved-corpus.jsonl \
  --manifest /path/to/approved-manifest.json \
  --output-dir artifacts/mkaos-mini-133m-run-001
```

For owner-created or explicitly rights-cleared local material that must not be redistributed, the owner must deliberately opt into the existing experimental-only gate by adding `--experimental-local-only`. That flag is not legal approval, does not approve third-party data, and does not permit checkpoint distribution. If the data are not cleared, do not train on them.

The wrapper checks the profile's exact parameter count and passes its architecture/training settings to the existing trainer. The trainer reports its hardware/memory preflight before model allocation. The actual corpus and training environment must be present; this repository profile alone cannot produce trained weights.

## Fixed evaluation, not one blended score

Keep `benchmarks/mkaos-general-llm-tr-001.json` fixed and held out. Collect one JSONL answer per case from each model/build, with the exact same prompts, decoding parameters and hardware. Example row:

```json
{"case_id":"gk-capital-001","answer":"Tokyo","latency_ms":25.1,"peak_memory_mb":620}
```

Score the answers:

```bash
python tools/evaluate_mkaos_answers.py \
  --dataset benchmarks/mkaos-general-llm-tr-001.json \
  --answers artifacts/mkaos-mini-answers.jsonl \
  --output artifacts/mkaos-mini-evaluation.json
```

The report separates scores by test category, lists missing/unexpected cases, estimates repeated four-gram output, and summarizes supplied latency and peak-memory measurements. Expected-term matching is a deterministic smoke metric only; it is not a factuality judge. A human must review factual claims, evidence/citations, Turkish quality, uncertainty, instruction compliance and harmful hallucinations. Do not tune on the held-out test cases.

For real speed/RAM comparison, also use `tools/benchmark_mkaos_device.py` on the same physical device and preserve the raw artifact hashes. Do not compare numbers from different machines or report whole-response latency as first-token latency.

## Release gates

1. Approved data and successful hardware preflight.
2. A real run with loss history, checkpoint hash and untouched test split.
3. No divergence/NaN and validation loss that improves without train/validation separation indicating overfit.
4. Per-category task evaluation plus human review, repetition, factuality and uncertainty checks.
5. Same-device latency/RAM comparison.
6. Subword tokenizer + Rust parity before treating this byte-level pilot as a production model.

Until these gates pass, this is an executable training plan and evaluation harness—not a trained, faster, or more intelligent MKAOS claim.

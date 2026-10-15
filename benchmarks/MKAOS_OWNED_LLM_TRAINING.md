# MKAOS-owned LLM training: first reproducible milestone

**Status: experimental training path. This is not a claim that MKAOS is already a competitive general-purpose LLM or fully sovereign.**

## What this milestone adds

- A project-authored UTF-8 byte tokenizer contract (byte IDs 0–255).
- A small causal Transformer language model defined in the training script, initialized from random parameters and trained only on a supplied audited manifest.
- Source-level split-leakage checks, explicit consent/permission fields, test-split isolation, deterministic seeds, loss logging and checkpoint SHA-256 reporting.
- An optional PyTorch development dependency; PyTorch is not added to MKAOS runtime requirements.
- A checkpoint and machine-readable report that explicitly mark the result as experimental and **not yet compatible with the Rust inference engine**.

## Prepare an audited dataset

First curate data with the existing governance tool. Each JSONL record must include `prompt`, `response`, `source_id`, `source_uri`, `license_id`, and explicit `consent: true`. Records must be human-reviewed and must not contain personal/sensitive data. Only licenses already allowlisted by `core/model_development.py` pass. The manifest's source-level train/validation/test split must contain multiple distinct sources in each split.

```bash
python tools/prepare_mkaos_training_dataset.py \
  --input data/mkaos-approved.jsonl \
  --output artifacts/mkaos-training-manifest.json \
  --report artifacts/mkaos-data-audit.json \
  --min-examples-per-split 2
```

The paths above are examples; the approved dataset must be supplied locally. This pipeline does not download a corpus, guarantee legal compliance, or automatically remove all PII.

## Train a tiny research checkpoint

Install PyTorch in a dedicated development environment (not the production/runtime environment), then run offline against the local manifest:

```bash
python tools/train_mkaos_owned_model.py \
  --manifest artifacts/mkaos-training-manifest.json \
  --output-dir artifacts/mkaos-byte-lm-run-001 \
  --steps 1000 --batch-size 16 --context-length 128 \
  --width 128 --layers 2 --heads 4 --seed 20261015 --device cpu
```

The output directory must not already exist. Keep the manifest, command, commit SHA, report and checkpoint together. For a network-isolated run, enforce isolation outside the script (for example, a container with no network) and record that fact separately; this script itself does not firewall the process.

## What the first model can and cannot do

This is a small byte-level language-model experiment. It learns only from the data actually supplied and will be far below large LLMs in world knowledge, reasoning and fluent generation. A tiny model trained on a tiny corpus is useful to validate the complete train/save/hash/evaluate loop, not to claim superiority over SmolLM2, Qwen, or Kumru. Byte-level generation is also inefficient compared with a mature subword tokenizer.

## Release gates before replacing SmolLM2 or Ollama

1. Train with a large, diverse, rights-cleared Turkish corpus and documented provenance.
2. Keep a held-out test split untouched; report perplexity/loss and task scores, factuality, instruction-following, repetition and human-reviewed Turkish outputs.
3. Implement the exact tokenizer and architecture in Rust; add golden-vector tests and checkpoint hash/shape validation.
4. Benchmark the owned checkpoint against SmolLM2/Qwen/Kumru on the same hardware, prompts, context, decoding settings and repeated cold/warm runs.
5. Measure real streaming TTFT only after correctness, quality, memory and throughput gates pass.
6. Promote only after a reviewable candidate release passes all gates. Until then, the external models remain comparison/test options; no random/untrained checkpoint becomes the default.

## General LLM capability roadmap

- **Phase 1 — Training loop correctness:** this script, deterministic data governance, checkpoint manifests, reproducible loss curves.
- **Phase 2 — Turkish language quality:** expand licensed data; train subword tokenizer; add spelling, morphology, instruction and reasoning datasets with human-reviewed held-out tests.
- **Phase 3 — Scale responsibly:** scale parameters and tokens only when validation loss improves without overfitting; use available GPU memory/compute evidence to choose sizes.
- **Phase 4 — Native runtime:** implement matching Rust tokenizer, multi-layer attention, positional encoding, normalization, output head and KV cache; verify logits/generation parity.
- **Phase 5 — Competitive evaluation:** compare on Turkish QA, math/logic, multi-step reasoning, factuality, coding and general knowledge. Publish scores and limitations, not marketing claims.

No training run or physical-device performance result is implied by merging this code. The real training checkpoint can only be produced in an environment with the audited dataset and optional training dependencies.

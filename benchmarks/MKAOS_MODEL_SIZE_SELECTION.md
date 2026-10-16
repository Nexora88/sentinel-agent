# MKAOS model size selection: measure before scaling

**Decision status (2026-10-16): 133M is a pilot target, not a proven optimum.** No real approved-corpus training run or independent quality comparison has been completed, so the repository must not describe 133M as the best size.

## Why 133,194,752 parameters?

The current profile `configs/mkaos/train-135m.json` fixes hidden size 1024, 11 decoder layers, 16 attention heads, 4 KV heads, intermediate size 3072 and a temporary 257-token byte vocabulary. That combination yields 133,194,752 parameters in the current trainer. It is a concrete engineering milestone that can be measured on a constrained GPU; the number was not selected from a completed model-size sweep.

## Why not smaller or larger now?

- **Smaller** models are cheaper and faster to iterate on, but may have less capacity for diverse Turkish instruction-following. This must be measured, not assumed.
- **133M** is a useful first architecture-validation target, but its temporary byte tokenizer is inefficient for Turkish UTF-8 and the current one-epoch/sequence-length-256 settings are only a smoke/pilot configuration, not evidence of a capable assistant.
- **Larger** models may use data more effectively when training data and compute are sufficient, but need more memory, compute, time and validated data. Scaling before data quality and tokenizer evaluation risks spending more for no demonstrated gain.

For scale intuition only, FP32 weight storage is approximately 4 bytes per parameter: 50M ≈ 200 MB, 133.2M ≈ 533 MB, and 300M ≈ 1.2 GB. These are **weights only**, not total training memory. FP32 Adam-style training also needs gradients and optimizer state; activations, temporary tensors, framework overhead and checkpoints add substantially more. Actual memory must be measured with the exact trainer and sequence length.

## Required decision experiment

Do not select the final size by parameter count alone. Before spending on long training runs:

1. **Tokenizer gate:** compare the current byte tokenizer with a reviewed Turkish-capable subword tokenizer. Measure average tokens per character/word, truncation, vocabulary size, and Rust/Python parity. Do not compare models using different prompt tokenization without documenting it.
2. **Data gate:** obtain accountable human approval for the exact source releases, privacy screening, train/validation/test split, attribution obligations, and model-weight distribution policy. Keep the training gate closed until the source register and manifest are evidence-backed.
3. **Pilot:** run a short, fixed-compute pilot for feasible model sizes on the same approved training subset. Record GPU model/VRAM, peak VRAM/RAM, tokens per second, wall time, training and validation loss, and failures.
4. **Quality comparison:** evaluate the same fixed Turkish development set and then a held-out test set with identical prompts and decoding settings. Report instruction following, Turkish fluency, factuality/evidence, uncertainty, repetition, latency and memory separately. Human-review factual claims; lexical keyword scores alone are insufficient.
5. **Choose by budgeted quality:** prefer the smallest model that meets explicitly written quality and runtime thresholds. Increase size only if the measured gain justifies the additional cost. Do not tune against the held-out test set.
6. **Reproducibility:** pin source/corpus/manifest hashes, tokenizer/model hashes, commit, seed, configuration and evaluation-set hash. Preserve reports and checkpoints according to the approved retention policy.

## Current blocker and next step

The source register currently has no approved sources and explicitly sets `corpus_ready=false` and `model_training_allowed=false`. No cloud GPU runner is provisioned in the repository configuration. Therefore, training must remain blocked. The existing GitHub Actions workflow expects a private self-hosted Linux x64 GPU runner and does not rent or provision a cloud GPU itself.

This document is an engineering decision framework, not a claim that training or a model-size sweep has occurred.

## Low-resource PC preparation

For the reported older i5 computer with 8 GB RAM and 40 GB free space, follow [`docs/MKAOS_LOW_RESOURCE_PC_PREP.md`](../docs/MKAOS_LOW_RESOURCE_PC_PREP.md) before installing dependencies or staging any dataset. It prioritizes system/disk health, a small smoke test, and keeping enough free space; it does not authorize or trigger training.

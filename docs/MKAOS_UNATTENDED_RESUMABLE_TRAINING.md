# MKAOS unattended/resumable training plan

**Status: architecture plan; no training run has started.** This document deliberately does not enable training or approve any dataset.

## Goal

The owner should not need to keep the older 8 GB RAM PC online or manually reconfigure every training session. Training must run on a separately available compute environment and recover safely after its session ends.

A powered-off PC contributes **zero compute**. It can be used later for offline corpus checks, evaluation, or inference, but cannot execute preprocessing/training while off. A cloud notebook is not a permanent worker: free sessions may end and compute quotas vary.

## Required pipeline

1. **Pinned data release and approval gate** — only exact source releases whose licence, privacy/PII, attribution, train/test leakage, retention, and intended model-weight distribution have been reviewed. Keep `data/mkaos/source-register.json` blocked until that evidence exists.
2. **Immutable corpus manifest** — record release/source IDs, per-file SHA-256, byte size, record count, tokenizer/version, split IDs and validation results. Store the corpus in private external storage, not in Git or public Actions artifacts.
3. **Streaming input** — read bounded JSONL shards instead of loading a 30 GB corpus into RAM. Deduplicate and split by source/document before training. Keep independent validation/test sets fixed.
4. **Preflight** — validate the manifest and approvals; verify free disk, RAM, GPU/VRAM, trainer compatibility, and checkpoint-store write/read access. Fail closed when any check fails.
5. **Durable resumable checkpoints** — at a configurable step/time interval, atomically save model, optimizer, scheduler, mixed-precision scaler (if used), global step, epoch, RNG states, data-shard/record cursor, and configuration/code/data/tokenizer hashes. Write to a temporary file, fsync if supported, then atomically rename. Keep a last-known-good checkpoint and at least one previous checkpoint.
6. **Resume validation** — resume only when architecture, tokenizer, training config, code revision and corpus/manifest hashes match. On mismatch, stop with a clear error; do not silently restart from random initialization or combine incompatible states.
7. **Interruption handling** — handle termination signals by requesting a final checkpoint when time permits. Resume from durable storage on the next available session. Do not depend on a free runner remaining alive or on ephemeral local disks.
8. **Evaluation and promotion** — produce a report with loss history, token/record counts, hashes, hardware, checkpoint identity, validation loss and independent test metrics. Do not automatically promote new weights to production. Keep model weights private until their redistribution policy is approved.

## Compute-provider reality

- The current GitHub workflow targets a pre-registered private self-hosted Linux x64 GPU runner. It does not provision a cloud GPU and cannot run when no matching runner is online.
- Free Kaggle notebook sessions offer a GPU when available, but saved notebook output space is documented as up to 20 GB; a single 30 GB corpus/output arrangement will not fit wholly in that saved workspace. See [Kaggle notebook documentation](https://www.kaggle.com/docs/notebooks).
- Colab free resources are not guaranteed; runtime limits and GPU availability vary. See [Colab FAQ](https://research.google.com/colaboratory/faq.html).
- Therefore the first cloud experiment should use a small, approved, reproducible shard and durable external storage. A provider-specific adapter and a verified resume path must be implemented before claiming unattended end-to-end training. Do not upload private or uncleared text to a third-party notebook.

## Parameter-count decision

Keep the current **133,194,752-parameter** profile as an engineering baseline for now. Do not increase it merely because the raw corpus is 30 GB.

Compare candidates only after the tokenizer is appropriate for Turkish, the number of usable training tokens is measured, and a fixed approved dataset/split exists. Suggested experimental stages:

- **~50M**: fast pipeline/debugging baseline.
- **~133M**: current baseline; measure tokens/sec, peak VRAM/RAM, validation loss and Turkish task performance.
- **~300M**: candidate only if the 133M model is data/quality-limited rather than compute-limited, and a measured run fits the available hardware and checkpoint budget.
- **~1B**: not the starting target for this project’s current free/low-resource setup. Training from scratch at this size would substantially increase compute, memory and checkpoint costs and should not be promised until a real hardware benchmark supports it.

These are comparison points, not a claim that a specific size is optimal. Raw GB is not a reliable proxy for token count: encoding, language mix, duplicates, markup and filtering change the usable token count. A better tokenizer can reduce waste without increasing model parameters.

## Implementation acceptance checklist

- [ ] Unit tests prove checkpoint round-trip restores model, optimizer, scheduler, step, RNG and data cursor.
- [ ] An interruption test stops a tiny run, resumes it, and matches an uninterrupted run within documented numeric tolerance.
- [ ] A changed corpus/config/tokenizer hash blocks resume.
- [ ] A simulated full disk / unavailable checkpoint store fails before training.
- [ ] Sharded streaming is tested on a synthetic corpus larger than available RAM without allocating it all in memory.
- [ ] The actual cloud provider is selected and its durable storage, quota, terms, and access controls are verified.
- [ ] Source approvals remain false until source-specific review is complete.

**Current blocker:** this repository state does not yet establish that the training code can restore the full optimizer/data-loader state after a preempted run, and there is no provisioned persistent cloud GPU worker. Do not call the pipeline automatic/resumable until the acceptance tests pass.

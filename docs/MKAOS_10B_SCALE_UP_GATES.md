# MKAOS 10B scale-up and cloud readiness

**Status: planning profile only; no 10B weights have been initialized or trained.** The exact dimensions in `configs/mkaos/train-10b.json` compute to **10,068,848,640 parameters**. The production source register still has zero approved sources and `model_training_allowed=false`.

## Recommended practical path before 10B scratch training

The near-term goal is a **validated small model and data/evaluation pipeline**, not a 10B scratch run. Keep the existing 133M and 1B profiles as controlled engineering pilots. A parameter count, successful loss reduction, or synthetic CI run is not evidence of useful Turkish assistant capability.

If a capable model is needed before MKAOS's own weights are ready, evaluate a separately registered, immutable-revision open-weight base model. Review its exact license and usage terms, local/offline compatibility, tokenizer, file hashes, and redistribution conditions before use. Only then test LoRA/PEFT fine-tuning as a separate adapter artifact against a frozen Turkish QA, coding, debugging, and source-grounding suite. Keep base-model and adapter provenance separate; never label third-party base weights or an adapter as a model trained from random initialization by MKAOS.

Advance to larger scratch-training profiles only when the small-run evidence demonstrates data quality, stable training, reproducible gains, and a justified hardware budget. Fine-tuning is a practical option, not an automatic license approval or a guarantee of quality.

## What exists and what is blocked

- The trainer has DDP, gradient checkpointing, epoch-boundary resume and optional optimizer-state sharding.
- DDP replicates model weights and gradients. Optimizer-state sharding does not shard model parameters, so it is not FSDP or ZeRO-3.
- The present memory preflight estimates an unsharded 16-bytes-per-parameter state and does not calculate a validated per-rank budget when optimizer states are sharded. It will likely block a large run; do not bypass it.
- No production tokenizer, approved training corpus, 10B hardware benchmark, private cloud runner, cloud budget cap, or retention policy is configured.

The checked-in 10B JSON is deliberately marked `planning_only` and `blocked`. It is not authorization to train, download, or use third-party model weights.

## Capacity planning, not a fit claim

For the exact 10.0688B profile, BF16-size weights alone are about 20.1 GB decimal (18.75 GiB). The trainer's simple 16-byte-per-parameter state estimate is about 161 GB decimal (150 GiB) before activations, communication buffers, checkpoint copies, fragmentation, and actual implementation behavior. The training code currently stores model parameters in FP32 while using autocast for compute, so BF16 weight arithmetic alone understates the required memory.

The JSON lists 16×80-GiB accelerators and 1 TiB host RAM as a conservative *planning floor*, with 32 accelerators and 2 TiB RAM recommended. These figures are not a validated fit; actual peak memory must be measured with the exact commit, topology, sequence length, precision, optimizer, and sharding configuration. A 20-token-per-parameter heuristic corresponds to roughly 201 billion training tokens; it is a planning heuristic, not a promise, approved-corpus size, or guarantee of quality.

The known local i5/8-GB machine cannot run this training profile. No provider has been selected and no cost estimate is embedded because cloud GPU price, region, availability and data-transfer charges change. Before any paid run, approve provider/account, region, accelerator count, maximum hourly and total spend, auto-shutdown, private storage/egress policy, dataset retention/deletion, and who can access checkpoints.

## Required sequence

1. Keep the 133M and 1B profiles as pipeline and scaling pilots. Record actual hardware, quality, throughput and resume behavior before advancing.
2. Replace the byte tokenizer with an independently reviewed Turkish-capable tokenizer and verify identical tokenization in training and inference.
3. Obtain a source-specific training, privacy, attribution and weight-distribution decision for every exact corpus release. Hash archives and selected files, screen PII/secrets, preserve provenance, deduplicate, separate source-level train/validation/test data, and keep test data out of training and tuning.
4. Fix the trainer's per-rank memory estimate and validate it on a small distributed run. Test optimizer-state sharding, checkpoint/resume after interruption, output/report integrity, and fail-closed source approval.
5. Select a private cloud runner and enforce required human reviewers through a configured GitHub environment. Use least-privilege identity, encrypted private storage, no public artifacts for corpus or checkpoints, explicit retention/deletion, audit logs, budget limits and automatic shutdown.
6. Run the fixed Turkish QA, coding, debugging and source-accuracy suite against the same baseline; record exact commit, tokenizer/model/data hashes, config, hardware, measured peak RAM/VRAM, latency, tokens/sec, training tokens and cost. Only scale when the measured improvement justifies the next spend.
7. Consider the 10B run only after every earlier gate is evidenced. Publish negative results and report parameter count separately from demonstrated capability.

## Reproducible planning commands

```sh
python tools/plan_mkaos_training_scale.py configs/mkaos/train-10b.json
python tools/plan_mkaos_scale.py --target-billions 10
```

Both commands estimate only. They do not download corpora or model weights, open approval gates, start a cloud job, or create trained parameters. The scale planner reports the computed rounded architecture count; the profile planner reports unsharded memory estimates and current implementation blockers. No result is a benchmark.


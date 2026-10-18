# MKAOS 50B scale-up gates

**Status: architectural target only. No MKAOS 50B checkpoint has been trained.** The current source register has no approved production data and keeps training disabled. The existing trainer is a single-process prototype; it does not implement distributed training, optimizer-state sharding, gradient checkpointing, or a production tokenizer.

## What “50B” means

The present planner estimates a dense decoder parameter count from explicit dimensions. A future MoE system must report total parameters and active parameters per token separately. A third-party base model, a LoRA adapter, and an MKAOS model trained from random initialization are different artifacts and must not be described as ownership or training of the same weights.

Run the estimate-only planner (default target 50B):

```sh
python tools/plan_mkaos_scale.py --target-billions 50
```

Use `--target-billions N` to model another scale. The report recomputes the count from rounded architecture dimensions. It does not download data or weights, inspect corpus contents, reserve cloud GPUs, or start training.

## Memory reality

For 50 billion dense parameters, raw parameter storage is about 100 GB (93 GiB) in BF16/FP16, or 25 GB (23.3 GiB) at nominal 4-bit before quantization scales, metadata, runtime buffers, and KV cache. Full Adam-style training state is roughly 800 GB (745 GiB) under the planner's simple 16-bytes-per-parameter estimate, before activations, communication buffers, and implementation overhead. These are arithmetic estimates, not a hardware fit guarantee.

The known local PC (i5, 8 GB RAM, about 200 GB free disk, GPU unknown) cannot train 50B from scratch. Even 4-bit inference weights exceed system RAM before overhead. A rented multi-GPU cloud run can be considered after a human approves the vendor, region, budget cap, retention and privacy settings, and exact model/data license scope. This repository change does not provision or charge for cloud resources.

## Staged path

1. Keep the existing 133M owned-model training attempt as a pipeline/provenance pilot only; the 12-record seed set is not capability training data.
2. Run small, immutable, rights-reviewed data and evaluation pilots. Keep training disabled until the source register contains exact release/file hashes, provenance, privacy review, attribution terms, separate weight-distribution decision, and accountable reviewer evidence.
3. Integrate licensed external weights as a pinned, isolated inference adapter first. Record publisher, model ID, immutable revision, declared license, license text/notice, configuration-derived parameter count, exact file hashes, and compatibility/evaluation results. License status is per model, not inferred from a hosting platform.
4. Only fine-tune after the exact base-model license permits the intended use. Prefer a parameter-efficient adapter when evidence shows it improves fixed Turkish QA, coding, debugging, and source-grounding tests. Keep base weights and adapter provenance distinct; do not merge or redistribute unless the license review allows it.
5. Increase from measured small-scale runs to multi-GPU pilots. Require checkpoint/resume, sharding, memory/throughput measurements, fault recovery, privacy controls, and reproducible quality gains before another size increase.
6. Consider 50B only after the earlier gates pass and a funded capacity plan supports the selected dense or MoE architecture. Record quality, latency, tokens/sec, peak RAM/VRAM, checkpoint size, training tokens and total cost. Do not use a larger parameter count as a quality claim.

## Candidate model review

Current official Hugging Face pages identify Qwen3-32B as Apache-2.0 and its model card reports 32.8B parameters. Mistral-Small-3.2-24B-Instruct-2506 is marked Apache-2.0 on its model page and publishes its architecture in `params.json`. These are candidates for review, not blanket approvals: pin an immutable revision, inspect complete license/notice and usage conditions, verify exact files and parameter count, assess privacy for the chosen serving route, then run the repository's Turkish evaluation suite. The model registry in `data/mkaos/source-register.json` records them as non-approved candidates. Do not use a moving `main` revision in an experiment report.

## Required stop conditions

- No data or model-weight download until the specific artifact is pinned and its access and license conditions are reviewed.
- No training while `model_training_allowed` is false or the exact manifest fails validation.
- No paid cloud launch before explicit vendor, region, budget, duration, retention, and privacy approval.
- No public release of weights or adapters until the exact source and base-model redistribution decisions cover that artifact.
- Any report without measured hardware and immutable model/data/code provenance must label metrics unavailable.



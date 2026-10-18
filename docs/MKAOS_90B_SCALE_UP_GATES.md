# MKAOS 90B scale-up gates

> Historical plan for the earlier 90B request. The active architectural target is 10B; see [MKAOS 10B scale-up and cloud readiness](MKAOS_10B_SCALE_UP_GATES.md). This document remains useful for its staged governance requirements, but its 90B sizing is no longer the active target.

**Status: target architecture and validation plan only.** MKAOS has not trained or released a 90-billion-parameter model. This document does not approve a dataset, reserve compute, or authorize a training run. The current source register remains authoritative and its closed gate must not be changed to make this plan pass.

The objective is to investigate whether a 90B-class MKAOS can be built responsibly, while shipping smaller useful stages first. “90B” must identify whether it means dense total parameters, total mixture-of-experts parameters, or active parameters per token. Those are different systems and must never be reported as interchangeable.

## Current blockers

Before any production training run:

- The source register must contain at least one exact, pinned source revision with documented source-specific training permission, provenance, attribution, privacy review, human review, and hashes. Its existing `model_training_allowed`, `corpus_ready`, and approved-source values remain unchanged until maintainers record evidence.
- Resolve the first-party smoke-corpus manifest hash mismatch and contradictory review metadata documented in [the corpus audit](MKAOS_CORPUS_AUDIT_2026-10-17.md). Do not silently regenerate hashes or infer approval.
- Keep the independent evaluation set out of training, tuning, and prompt development. Record who controls it and every access.
- Obtain a written compute and cost plan, a tested recovery path, and an explicit human go/no-go for each scale-up stage.

## Staged program

| Stage | Work | Exit evidence |
|---|---|---|
| 0. Provenance | Reconcile first-party records; review every candidate source and exact revision; scan privacy risks; build immutable, source-level splits and manifests. | Corpus gate passes for the intended use; reproducible hashes; documented attribution and weight-distribution decision. No third-party candidate is presumed approved. |
| 1. Measurement baseline | Run the same frozen Turkish QA, coding, debugging, source-grounding, safety, and refusal tasks against available baselines and the current MKAOS implementation. | Versioned raw outputs, scoring rubric, sample counts, independent human scores, errors, and hardware/runtime metadata. Label smoke results as smoke results. |
| 2. Pipeline proof | Train a small from-scratch checkpoint or an explicitly licensed adapter; save, reload, resume, and evaluate it from a reviewed manifest. | Repeatable loss curves and artifact hashes; train/validation/test isolation; checkpoint and tokenizer compatibility; recovery and failure tests. |
| 3. Useful model scale | Increase model/data/sequence length only after the prior stage passes. Evaluate full fine-tuning versus LoRA/adapters on a legally compatible base model and on MKAOS-owned weights as separate experiments. | Quality improvement on untouched tasks, bounded regressions, measured cost, and hardware headroom. Publish negative results too. |
| 4. Distributed feasibility | Benchmark scaling efficiency, interconnect, storage throughput, checkpointing, fault recovery, and serving load using representative runs before committing to a 90B run. | Reproducible multi-node profile and funded capacity plan with explicit throughput, storage, energy, and recovery targets. |
| 5. 90B go/no-go | Select dense or MoE design and training method using evidence from earlier stages. Approve the exact corpus, base weights (if any), compute allocation, safety plan, and release rights. | Signed review record; no unresolved rights/privacy gate; pre-registered evaluation and release criteria. If any gate fails, remain at the best validated smaller scale. |

LoRA reduces the number of trainable parameters; it does not remove the need to load the base model or account for activations, context, optimizer state, and runtime overhead. Fine-tuning a third-party base model also requires a separately reviewed base-model license and provenance.

## Capacity estimates are planning bounds, not benchmark results

For a **dense** 90-billion-parameter model, parameter storage alone is approximately 180 GB (about 168 GiB) in BF16, or 45 GB (about 42 GiB) at 4-bit. These arithmetic estimates exclude quantization metadata, runtime buffers, activations, attention/KV cache, fragmentation, and operating-system memory. They do not establish that a particular device can load or train the model.

Full training memory depends on optimizer, precision, sharding, sequence length, batch size, activation checkpointing, and parallelism; it can be several times the parameter storage. Measure actual peak accelerator and host memory on the selected stack and include a safety margin. Do not infer VRAM needs from parameter count alone, and do not advertise a 90B local tier without a tested hardware matrix.

Every capacity report should state whether the number is measured or calculated, the exact model/checkpoint hash, precision/quantization, context length, batch/concurrency, runtime commit, device(s), peak RAM/VRAM, and measurement method.

## Quality and performance release report

Use a frozen, versioned evaluation suite with separate Turkish QA, professional code generation, code repair/debugging, factual/source attribution, and safety subsets. Keep prompts, scoring rules, and test examples fixed for a report; disclose sample sizes and evaluator agreement. Report task-level results and common failures alongside aggregate scores.

`tools/evaluate_mkaos_turkish_tasks.py` accepts `coding`, `debugging`, and `source_accuracy` as task categories. Each such case must include `automated_checks: [{"name": "...", "passed": true}]`. A coding/debugging harness must execute generated code in an isolated environment; a separately reviewed citation checker must provide source-accuracy checks. The evaluator records pass rates and prediction hashes but does not execute code or independently verify citations. Reports must retain the exact checkpoint, harness/checker version, and benchmark revision. Do not count an absent check as a pass.

For every real-model performance run record:

- model and tokenizer identifiers and SHA-256 hashes, model architecture/parameter-count definition, and base-model/license details;
- dataset and evaluation revision identifiers without exposing private or restricted examples;
- hardware model, memory, operating system, driver/runtime versions, precision, quantization, context, and concurrency;
- warm-up policy, number of repeats, median and p95 first-token and end-to-end latency, generated tokens/second, peak RAM/VRAM, failures, and output hashes;
- whether each result is measured on real weights, synthetic weights, a reference model, or estimated.

Synthetic weights test engine correctness only. A fallback model's score is not an MKAOS score. Never publish estimated metrics as measured results.

## Multimodal boundaries

Treat local image understanding, video-frame analysis, and text-to-video generation as separate capabilities and model integrations:

1. Image understanding: document supported formats, maximum input size, local processing behavior, model/license, and image-task evaluation.
2. Video understanding: `analyze_video_frames` is a separate optional adapter that samples deterministic timestamps from a local file and invokes the local image model per frame. It has explicit file-size, duration, frame-count, and frame-size limits. Frame analysis is not full temporal understanding; test on a separate video set.
3. Text-to-video: `text_to_video` is a distinct adapter contract and accepts only an explicitly marked local backend. No neural text-to-video model is bundled or claimed. Integrate a concrete model only after its weights, license, hardware requirements, safety behavior, storage, and offline operation are reviewed. Do not describe slideshow, animation, or image sequences as genuine text-to-video generation.
4. Keep each adapter optional and resource-gated; report download/storage requirements and whether any external service is contacted.

## CI and operating rules

CI may validate schemas, deterministic manifests/splits, closed-gate behavior, evaluation report completeness, adapter contracts, and small CPU smoke paths. CI must not download restricted corpora, open the training gate, publish checkpoints, or claim real-model quality from fixtures.

Before merge, run the repository's applicable corpus, training-manifest, evaluation, media-adapter, and offline tests. Hardware claims require runs on named real devices and remain “not tested” for absent platforms. This document is successful only when it makes missing evidence visible; it does not itself satisfy any training or release gate.


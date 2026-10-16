# MKAOS: next research gate — offline runtime and owned-model evidence

This plan advances implementation without claiming that a frontier-level model or a fully owned stack already exists. Every gate needs an artifact and a reproducible result.

## What can improve on indie hardware

A single developer cannot reasonably reproduce the training compute of frontier systems. The credible strategy is to make a smaller system better at a defined set of tasks, then widen that scope based on measurements:

1. **Data quality before scale.** Curate only reviewed Turkish text with documented training permission, privacy clearance, provenance, deduplication and non-overlapping train/validation/test splits. The current source register has zero approved sources; this is a hard stop, not a paperwork detail.
2. **Tokenizer before parameter scaling.** The current owned-model path uses UTF-8 byte IDs (257-token vocabulary). It is simple and independently implemented, but inefficient for Turkish text and limits how much linguistic context fits in a small sequence window. Research a native, reproducible subword tokenizer only with an explicit format/version contract and Rust parity tests; do not silently change existing checkpoints.
3. **Measure reasoning by task.** Establish the same held-out tasks for arithmetic, multi-step constraints, Turkish instruction following, code, factuality and repetition. Compare checkpoints by category, not a single flattering average. Keep test examples out of training and model selection.
4. **Improve training stability.** Track seed, optimizer, learning-rate schedule, gradient clipping, train/validation loss, best-checkpoint selection and wall-clock/resource use. Run small ablations with fixed seeds before spending scarce compute.
5. **Use CPU first, accelerators when available.** Reduce sequence length/model width for experiments; add batch/gradient accumulation only when tests show equivalence. Do not advertise CUDA, ROCm, Metal, Gaudi or NPU support without real device tests.
6. **No hidden teacher dependency.** Distillation from an external model can improve a student, but it does not meet a strict no-foreign-model requirement and may have licensing constraints. It must not be presented as fully independent.
7. **Release evidence, not slogans.** Publish the checkpoint hash, tokenizer hash/version, corpus manifest hash, training commit, configuration, environment, losses, held-out metrics and limitations. A checkpoint is not accepted into default chat solely because it loads.

## Offline operation: what the repository can and cannot prove

The default/offline Compose profile is intended to keep runtime containers on an internal Docker network and disables web, finance, scanning and external notifications. Images, packages and model artifacts must be prepared before isolation. A local network test and a valid Compose file are useful evidence, but neither proves the host operating system has no egress.

Before declaring a machine air-gapped:

- build and cache all required images/dependencies before disconnecting;
- put the runtime on the offline Compose overlay;
- run the repository's offline egress validation from the actual deployed container;
- inspect the resolved Compose configuration and Docker network;
- add host firewall/VM isolation, then verify it from that host;
- record exact machine, OS, Docker version, network state, test timestamp and result;
- do not put private prompts, user data or secrets in a public benchmark report.

The evaluator added in this step (tools/evaluate_mkaos_owned_checkpoint.py) uses only a local checkpoint, an already-built Rust CLI and a local JSON dataset. It has no model downloader or HTTP client. Its substring and repetition metrics are smoke checks, not a semantic benchmark or legal provenance check.

## Candidate checkpoint evaluation

Build the CLI before the offline run:

    cargo build --release --manifest-path engine/mkaos-inference/Cargo.toml --bin mkaos-generate

Then evaluate a local candidate (use the dimensions from its training report):

    python tools/evaluate_mkaos_owned_checkpoint.py \
      --generator target/release/mkaos-generate \
      --checkpoint artifacts/mkaos-tr/mkaos-owned.mkaosw \
      --expected-sha256 YOUR_REVIEWED_SHA256 \
      --heads 4 --kv-heads 2 --max-seq 2048 \
      --max-new-tokens 64 \
      --output artifacts/mkaos-owned-quality-report.json

On Windows, use the locally built target/release/mkaos-generate.exe path. Do not use a fake hash: the expected hash is optional for local exploration, but required by a release process. The report stores generated answers. Keep it local if prompts or answers contain private information.

## Exit criteria before claiming independent model ownership

- A non-empty, reviewed source register with verifiable evidence and permission for the intended use.
- A corpus archive and per-sample manifest whose hashes are generated from actual files.
- A successful non-synthetic training run from random initialization, with logs and a reproducible configuration.
- A checkpoint and tokenizer with recorded hashes and explicit versions.
- Successful checkpoint load and generation using the Rust engine, plus repeatable tests.
- Independent held-out Turkish reasoning evaluations with human grading, task-level error analysis and comparisons against baselines.
- RAM, latency, tokens/second, thermal/stability measurements on each claimed target class.
- Offline egress checks at container and host/VM layers.
- Explicitly recorded licenses for every retained dependency, model asset and dataset.

Until those gates pass, the honest status remains: **independent engine development is underway; independent, capable MKAOS model training and universal offline isolation are not yet demonstrated.**

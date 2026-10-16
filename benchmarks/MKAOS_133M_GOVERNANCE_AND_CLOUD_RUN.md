# MKAOS 133M training: governance and cloud-runner operations

**Current state (2026-10-16): BLOCKED — no source is approved for training.** The source register deliberately has an empty `current_approved_sources` list and sets both `corpus_ready` and `model_training_allowed` to false. Do not change these flags merely to make CI green. The existing Turkish Wikipedia dump preparation workflow verifies/downloads a source and produces a sample-review sheet; it does not grant training rights or complete the review.

Model-size rationale and the required empirical comparison plan are documented in [MKAOS_MODEL_SIZE_SELECTION.md](MKAOS_MODEL_SIZE_SELECTION.md). The current 133M profile is a pilot target, not a proven optimum.

## 1. Evidence needed before approval

For every exact source and release, a qualified human reviewer must complete and attach evidence for:

- [ ] Canonical publisher page and exact release/version/date.
- [ ] Original archive and selected corpus-file SHA-256 values, file sizes, and immutable download provenance.
- [ ] License text/version and analysis of text rights, attribution/share-alike, exceptions, and generative-model training compatibility.
- [ ] Separate decision on whether resulting model weights may be redistributed. Dataset packaging licence alone is not proof of this.
- [ ] Personal-data/PII, secrets, contact information, sensitive-data and minors-related-content screening plan and results; documented exclusions and escalation policy.
- [ ] Human sample review with sample method, number reviewed, reviewer/date, categories, decisions, and unresolved findings.
- [ ] Duplicate/near-duplicate checks and document/source-level train/validation/test leakage checks.
- [ ] Exact manifest SHA-256 and signed or attributable reviewer decision.
- [ ] Retention/deletion policy and artifact access policy.
- [ ] Explicit outcome: `approved`, `blocked`, or `approved_local_only_no_weight_distribution`, with scope and limitations.

The project owner's request to proceed is not a third-party licence and cannot substitute for a human/legal decision. Do not describe this review as completed until evidence and a named accountable reviewer decision are present. This file is a checklist, not legal advice.

## 2. Private GPU runner setup

The workflow `.github/workflows/mkaos-approved-training.yml` intentionally requires a **self-hosted** runner labelled `mkaos-training`, `gpu`, and `ram-16g`; GitHub-hosted CPU runners are not used for this job.

Configure a dedicated private Linux x64 runner with:
- a supported CUDA/ROCm PyTorch installation visible to the runner account;
- at least 16 GiB system RAM as a planning floor (32 GiB recommended), adequate accelerator memory, and at least 10 GiB free persistent storage;
- approved corpus and manifest stored outside the Git checkout, readable only by the training runner;
- writable persistent checkpoint directory `/opt/mkaos-private-checkpoints`;
- restricted repository access and runner isolation (no unrelated secrets or production credentials).

In repository Settings → Environments, create `mkaos-training-approved`, add required reviewers, and limit deployment branches. An environment name alone does not create an approval gate; configure required reviewers explicitly. Never use a public/shared runner for private data.

## 3. Dispatch only after approval

After human review has approved the exact source release and intended weight policy, update `data/mkaos/source-register.json` with evidence-backed source status and only then set `current_approved_sources`, `corpus_ready`, and `model_training_allowed` consistently. The manifest must pass `tools/validate_mkaos_training_manifest.py` and match the exact JSONL corpus records and hashes.

Then run **Actions → MKAOS approved 133M training (self-hosted GPU only) → Run workflow** and provide:
- approval reference to the review record;
- absolute path to the private JSONL corpus;
- absolute path to the matching provenance manifest.

The job re-checks the source register, accelerator, memory/disk prerequisites, and manifest before calling `tools/train_mkaos_profile.py`. The existing trainer still performs its own strict checks and memory preflight. A failed gate is a successful safety outcome, not a failed model-training claim.

## 4. Outputs and retention

A completed run must produce:
- `training-report.json` with source/corpus/manifest hashes, exact parameter count, hardware, train/validation history, best validation loss and independent test loss;
- `loss-history.csv` and `loss-curve.svg`;
- `mkaos-owned.mkaosw` with a SHA-256 and resumable `trainer-checkpoints/latest.pt`.

Model weights and resumable checkpoints stay on the private persistent runner disk. The workflow uploads only non-sensitive report/curve metadata, never corpus or model weights. Back up checkpoints to a restricted encrypted store under the approved retention policy; do not copy them into Git or public Actions artifacts. If the runner's persistent volume is not backed up, local retention is not a durable backup.

## 5. Fixed comparison and release decision

Use the same versioned test set, prompts, decoding options, software commit, device and repeat count for baseline and new model. Preserve raw answer JSONL, evaluator output, hardware metadata, tokenizer/model hashes, and human review. Report per-category instruction-following, Turkish quality, factuality/evidence/uncertainty, repeated output, p50/p95 latency, tokens/second, and peak RAM/VRAM separately. The current lexical expected-term evaluator is only a smoke test; human factuality and evidence review is mandatory.

Do not tune on the held-out test split. Fix failures on a separate development set, then rerun the unchanged test set. Do not claim speed or quality improvements without same-device measurements.


## Fixed baseline-versus-candidate report

Generate both answer JSONL files with the same exact prompts, generation settings, and hardware, then run the evaluator on each with the same dataset file:

```bash
python tools/evaluate_mkaos_answers.py --dataset benchmarks/mkaos-general-llm-tr-001.json --answers artifacts/baseline-answers.jsonl --output artifacts/baseline-report.json
python tools/evaluate_mkaos_answers.py --dataset benchmarks/mkaos-general-llm-tr-001.json --answers artifacts/candidate-answers.jsonl --output artifacts/candidate-report.json
python tools/compare_mkaos_evaluations.py --baseline artifacts/baseline-report.json --candidate artifacts/candidate-report.json --output artifacts/fixed-test-comparison.json
```

The evaluator records the dataset file SHA-256. The comparison tool refuses reports whose dataset hash or case IDs differ, and reports per-category deltas, improved/regressed case IDs, repeated four-gram ratio, median/p95 latency, and peak memory. This does not replace human factuality/evidence review. Use `tools/benchmark_mkaos_device.py` for same-device tokens/sec and runtime memory measurements.

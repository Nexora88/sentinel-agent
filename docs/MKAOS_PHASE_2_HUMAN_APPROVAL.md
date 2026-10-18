# MKAOS Phase 2 — Human review handoff (no approval recorded)

Status: **WAITING FOR HUMAN REVIEW — TRAINING GATE CLOSED**

This document prepares the next phase. It does not approve a source, dataset, training run, or weight distribution.

## What was recovered in Phase 1

- Workflow run: https://github.com/Nexora88/sentinel-agent/actions/runs/39064724746
- Dataset ID: `mkaos-trwiki-20260901-cleaned-v1`
- Report artifact: `mkaos-wikimedia-corpus-report`
- The manifest and 30-record sample-review sheet were recovered and their file hashes checked.
- Sample review status at recovery: **30 pending, 0 approved, 0 rejected**.
- Prepared `train.jsonl`, `validation.jsonl`, and `test.jsonl` shards were not included in the recovered report artifact. Their expected hashes are recorded in the manifest, but the files themselves still need recovery/regeneration and independent verification.
- The source register still has an empty `current_approved_sources`, `corpus_ready=false`, and `model_training_allowed=false`.

## Review decisions — do not tick until actually checked

### A. Exact source and release
- [ ] I reviewed the exact Turkish Wikipedia dump release `20260901` and the source-specific terms/exceptions.
- [ ] I understand that a public dump does not by itself settle permission to train a generative model or distribute derived weights.
- [ ] I reviewed attribution, share-alike, modification-notice, and imported-content obligations with suitable evidence.
- Evidence/reference: **not recorded**

### B. Sample content and privacy
- [ ] I inspected all 30 records in `sample-review.json`, not just the summary.
- [ ] Each sample is appropriate for training and does not expose personal, confidential, secret, or otherwise sensitive information.
- [ ] I recorded an individual decision for each record; no bulk approval by default.
- [ ] I understand that a 30-record sample is not a full-corpus privacy/content clearance.
- Evidence/reference: **not recorded**

### C. Scope of permission — these are separate decisions
Choose only after review:
- Training use: **PENDING**
- Private/local-only checkpoint experiment: **PENDING**
- Public or third-party checkpoint/weight distribution: **PENDING**
- Attribution and source-notice plan: **PENDING**

A decision allowing private training does **not** automatically allow publication or redistribution of weights.

### D. Reproducibility and splits
- [ ] Recover or regenerate all three JSONL split files from the pinned source and reviewed preparation code.
- [ ] Verify actual SHA-256 for every split against the manifest.
- [ ] Verify source/document-level split separation, duplicate handling, and that the independent test split is not used for training or checkpoint selection.
- [ ] Preserve source revision, script revision, environment, and generated file hashes.
- Status: **NOT COMPLETE**

## Decision record — fill only after the review

- Reviewer identity/role:
- Review date (UTC):
- Source/release and manifest SHA-256:
- Rights/training decision: `approve` / `reject` / `needs_review`
- Privacy/content decision:
- Attribution/share-alike decision and evidence:
- Private-training permission:
- Weight-distribution permission: `approved` / `not approved` / `not reviewed`
- Conditions and evidence links:

## Gate policy

Until this review is documented, keep `data/mkaos/source-register.json` unchanged with no approved source and keep the training gate closed. Do not start the approved 133M workflow, do not set `model_training_allowed=true`, and do not publish weights. Once review is complete, record the decision in the repository and run the existing strict validators before any training.

The existing approved-training workflow also requires a trusted self-hosted Linux x64 GPU runner with labels `mkaos-training`, `gpu`, and `ram-16g`, at least 10 GiB free in `/opt/mkaos-private-checkpoints`, and a private approved corpus/manifest. A successful metadata check is not legal clearance or evidence of useful Turkish capability.

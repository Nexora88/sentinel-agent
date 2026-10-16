# MKAOS first-party Turkish smoke corpus

This is a tiny, AI-assisted original diagnostic set for testing the from-scratch training pipeline; it is **not** a useful general-purpose language-model corpus.

- Corpus: `first-party-smoke-v1.jsonl`
- Provenance manifest: `first-party-smoke-v1.manifest.json`
- Splits: 4 train, 4 validation, 4 independent test records; each record has a SHA-256 of its exact UTF-8 text.
- Owner authorization: on 2026-10-16 the project owner approved these exact 12 records for a bounded local-only, non-redistributable experiment. This approval is recorded in the manifest.
- Rights status: `license_reviewed=false`; the proposed CC0 label remains unapproved. The owner authorization is **not** a third-party license decision or legal review.
- Experiment status: the workflow may train from random initialization, run the exact checkpoint through Rust, report its SHA-256 and metrics, then delete the checkpoint before workflow completion. It must not upload or distribute model weights.
- Production gate: `data/mkaos/source-register.json` remains fail-closed with no approved production sources and `model_training_allowed=false`.
- Independent test split must not be used for gradient updates or model selection.

The experiment can demonstrate the mechanics of an owned training/export/inference path only. Twelve short records cannot establish useful Turkish language ability, reasoning, or production readiness.

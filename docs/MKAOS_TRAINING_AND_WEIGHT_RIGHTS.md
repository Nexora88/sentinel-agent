# MKAOS training-data and checkpoint rights: two independent decisions

The training pipeline must not treat “permission to train” and “permission to publish weights” as the same decision.

## Source approval scopes

- `internal_nonredistributable`: a pinned source release may be used for the explicitly approved private/internal training run. Checkpoint files and derived weights must remain private; workflow artifacts must not be publicly uploaded.
- `redistributable`: training is allowed only when the source's separate `weight_distribution_review` is `approved` as well as source-specific training, provenance, privacy, and attribution checks.

Every approved source must still have a pinned `approved_revision`, a source-specific `approval_evidence` reference, and `permitted_use_now=true`. This change does not auto-approve Wikipedia, Common Voice, Tatoeba, HPLT, or any other candidate source. It does not alter the currently empty approved-source list or set `model_training_allowed=true`.

## What this fixes

Previously, the normal training gate required `weight_distribution_review=approved` before *any* training could begin. That coupled internal research to public checkpoint-distribution rights and made the policy unnecessarily restrictive. The gate now allows an explicitly reviewed source to be used for internal non-redistributable training while the weight-distribution decision remains pending.

## What remains mandatory

- Exact source/release and archive or selected-file SHA-256 values.
- Source-specific license terms, attribution obligations, and upstream exceptions.
- Privacy/PII/secrets screening and human content review.
- Train/validation/test separation by document/source, not random overlapping chunks.
- Explicit weight-distribution review before publishing checkpoint files or model weights.
- Independent Turkish and task-quality evaluation. Loss alone is not a human-competence score.

This is a workflow-policy improvement, not legal advice and not a declaration that any candidate dataset is approved.

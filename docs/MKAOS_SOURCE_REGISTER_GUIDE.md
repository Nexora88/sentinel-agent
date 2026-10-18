# MKAOS source register template

This is an intentionally empty template. **Do not add invented sources or mark a row approved to satisfy a gate.** Make one row per source/dataset version, not one row per broad website or institution.

Copy this file outside the repository for working records if source URLs, reviewer identities, or internal notes are confidential. Do not commit raw archives, copyrighted content, personal data, API keys, private correspondence, or legal documents.

## Fields

- `source_id`: stable internal identifier, unique per source snapshot.
- `source_uri`: exact source/dataset URL or documented local archive reference.
- `source_type`: for example `arxiv-paper`, `arxiv-dataset`, `turkish-public-record`, `university-dataset`, `code-repository`, `licensed-corpus`.
- `version_or_snapshot`: version, release, commit, DOI, archive date, or other reproducible identifier.
- `acquired_at_utc`: ISO-8601 UTC acquisition time.
- `license_id`: exact licence identifier/version; use `UNKNOWN` until verified.
- `license_evidence_uri`: link or local evidence reference to the actual licence/terms.
- `attribution_requirement`: `required`, `not-required`, or `unknown`; approved records cannot leave this undecided.
- `attribution_evidence_uri`: evidence for the attribution decision and the retained attribution plan/records.
- `training_permission`: `yes`, `no`, or `unknown` based on reviewed evidence, not guesswork.
- `redistribution_permission`: `yes`, `no`, or `unknown`; separate from training permission.
- `privacy_review`: `passed`, `blocked`, or `not-reviewed`.
- `privacy_evidence_uri`: evidence for the source-specific privacy review; required for approval.
- JSON source-registry approvals also require a nested `rights_review` with reviewer, date, evidence references, an affirmative training decision, a passed privacy review, and a concrete attribution requirement/plan. Missing evidence fails closed in the training gate.
- `reviewer_id`: human reviewer reference, not a public person's full details.
- `review_date`: ISO date.
- `decision`: `approved`, `quarantine`, or `rejected`.
- `notes`: concise rationale and restrictions; avoid copying sensitive material here.

## Review rules

1. Review the exact version acquired. A paper's hosting platform does not automatically license its text, cited dataset, code, or figures for model training.
2. For Turkish-language material, assess the specific collection's terms, copyright status, attribution obligations, personal-data risks, and any archive access restrictions. “Publicly accessible” is not the same as “public domain.”
3. Record training and redistribution permission separately. Do not infer either from an SPDX label alone.
4. Keep ambiguous records in quarantine and out of the training manifest.
5. The reviewer records the decision and evidence; scripts can validate fields but cannot provide legal advice or sign off on behalf of a rights holder.
6. Preserve acquisition details and the SHA-256 inventory for the exact local files. Re-hash after transfer and before training.

## Required before training

- Every training record maps to an approved source ID and exact source snapshot.
- All records have an evidence-backed licence/permission decision and passed privacy review.
- The human reviewer has reviewed the actual licence terms and any additional permissions required.
- Train/validation/test splits are separated by source, not merely by randomly splitting adjacent text chunks.
- A held-out test set remains excluded from training, tuning and model selection.
- The source register, data manifest, archive inventory and training run metadata are versioned together by hashes.

This template starts empty by design. An empty register is an honest blocker, not a completed audit.

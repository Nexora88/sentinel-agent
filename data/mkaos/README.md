# MKAOS first-party Turkish smoke corpus (draft)

This is a tiny, original diagnostic set for testing the data pipeline; it is **not** a useful general-purpose language-model corpus.

- Corpus: `first-party-smoke-v1.jsonl`
- Provenance manifest: `first-party-smoke-v1.manifest.json`
- Splits: 4 train, 4 validation, 4 independent test records; each record has a SHA-256 of its exact UTF-8 text.
- Intended content: software/model-development statements; no third-party text was intentionally copied and no personal data is intended.
- Rights status: **pending human maintainer review**. The proposed CC0 label is not an approval. The AI-assisted draft's authorship/publication rights and the repository's redistribution terms must be explicitly confirmed.
- Training status: not approved for the standard training path. Do not change `human_review` or `license_reviewed` to approved merely to make the validator pass. Any local-only experiment must use the existing explicit experimental gate and must not distribute its checkpoint.
- Independent test split must not be used for gradient updates or model selection.

This file records a candidate, not a legal conclusion or a claim that MKAOS has been trained.

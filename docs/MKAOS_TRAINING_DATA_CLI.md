# MKAOS training-data preparation CLI

This is a local, offline preparation step for a future MKAOS training pipeline.
It validates a UTF-8 JSONL file using `core/model_development.py`, rejects
unknown licenses and missing explicit consent, deduplicates by content hash,
and assigns all examples from one source to the same deterministic split.

Each input JSONL record must include:

```json
{
  "prompt": "A reviewed Turkish instruction",
  "response": "A reviewed answer",
  "source_id": "source-unique-id",
  "source_uri": "https://example.org/dataset-card",
  "license_id": "CC-BY-4.0",
  "consent": true,
  "review_status": "approved"
}
```

This example is a schema illustration, not a recommendation to use that URL or
to assume that a licence automatically grants every training right. Verify the
actual dataset terms, attribution requirements, source provenance, privacy
basis, and whether model training and redistribution are permitted before
including any records. The allowlist is a technical filter, not legal advice.
The current code is not a complete PII detector.

## Run

```bash
python -m tools.prepare_mkaos_training_dataset \
  --input ./private-data/reviewed-tr.jsonl \
  --output ./artifacts/mkaos-training-manifest.json \
  --report ./artifacts/mkaos-training-report.json \
  --min-examples-per-split 100
```

The command does not download data or call remote services. It refuses to
overwrite existing output files. It blocks the training manifest unless
train, validation, and test each meet the configured minimum. Because splits
are source-level, small datasets can be blocked even when they contain many
rows. The output contains the approved prompt/response records and should be
stored with the same privacy controls as the source dataset; the report
contains summary counts and rejection reasons.

**This tool does not train or alter weights.** A separate trainer must consume
the reviewed manifest, log the code/runtime/hyperparameters and artifact hashes,
evaluate on a frozen held-out set, and require human approval before a release.
The Rust byte tokenizer and synthetic decoder are not yet a complete, trained
MKAOS language model.

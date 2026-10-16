# MKAOS source-register enforcement

Run the schema and consistency check before reviewing a dataset:

```bash
python tools/validate_mkaos_source_register.py
```

The empty template is valid but intentionally reports zero approved sources. To make a data-preparation/training job require at least one approved record:

```bash
python tools/validate_mkaos_source_register.py --register ./local-data/mkaos-source-register.tsv --require-approved
```

An approved record must explicitly declare training permission, passed privacy review, a concrete licence identifier, evidence URI, reviewer reference and review date. Unknown or incomplete entries must remain in quarantine. The validator checks schema and internal consistency only; it does not visit evidence links, authenticate the reviewer, interpret licence terms, or determine whether a licence covers model training.

Keep actual corpora, private evidence and internal reviewer details outside Git unless publication has separately been cleared. Hash the exact local archive and extracted files with `tools/hash_mkaos_sources.py`; verify that inventory immediately before preparing the training manifest. A matching SHA-256 establishes byte integrity, not lawful provenance or training permission.

## Gate status

- Schema validation: automated.
- Local file hashes: automated by the separate hash inventory tool.
- Licence and attribution review: human evidence review required.
- Privacy and personal-data screening: human review required.
- Permission to train: evidence-backed human sign-off required.
- Actual corpus availability: not implied by a valid empty template.

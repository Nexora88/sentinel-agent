# MKAOS Turkish training source-rights dossier — 2026-10-16

**Overall decision: BLOCKED / PENDING HUMAN REVIEW.** This dossier records evidence locations and unresolved questions. It is not a legal opinion. No listed source is approved for training, commercial use, raw-data redistribution, or model-weight distribution by this file.

## Required evidence record for every release

For each source, attach the exact release/version, original archive and selected-file SHA-256, file size, acquisition timestamp, terms/license snapshot, reviewer identity/date, source-level rights analysis, privacy/content sample results, and a separate model-weight distribution decision. The workflow must stop when an evidence field is missing. A public license label alone is not an approval.

| Source | Pinned candidate | Primary evidence to inspect | Local hashes | Human decision |
|---|---|---|---|---|
| Turkish Wikipedia | Wikimedia trwiki-20260901-pages-articles-multistream.xml.bz2 | [Official dump directory](https://dumps.wikimedia.org/trwiki/20260901/), [Wikimedia Terms of Use](https://foundation.wikimedia.org/wiki/Terms_of_Use), [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | Generated only after workflow downloads the exact archive and writes a manifest; not yet available in this dossier | Pending: imported-content exceptions, attribution/share-alike implications, privacy and model-weight distribution |
| Mozilla Common Voice Turkish text | Scripted Speech 27.0, Turkish (tr), dataset ID cmu5wkah500c2o10719lem8m8; candidate release date 2026-09-17 | [Mozilla Data Collective dataset page](https://mozilladatacollective.com/datasets/cmu5wkah500c2o10719lem8m8), datasheet and applicable terms linked from that page | Archive and exact selected TSV SHA-256 not supplied; do not substitute guessed hashes | Pending: permitted access, no re-hosting restriction, source mix (including Wikipedia/SETimes/Other), privacy and model-weight implications |
| Tatoeba Turkish text | Exact export/version not pinned; do not download into training yet | [Official downloads](https://tatoeba.org/en/downloads), [Tatoeba terms](https://tatoeba.org/en/terms_of_use) | Not available; exact export and row-level provenance hashes required | Pending: exact sentence licenses/attribution, exclude audio unless separately cleared, weight distribution |
| HPLT Turkish cleaned text | HPLT v2.0 tur-Latn candidate; exact package not pinned | [Official HPLT v2.0 dataset page](https://hplt-project.org/datasets/v2.0) and linked package documentation/terms | Not available; package URL, bytes, SHA-256 and subset hash required | Pending: packaging license versus underlying web-content rights, privacy, downstream obligations and weight distribution |

## Non-negotiable gates

- Training-use decision and model-weight distribution decision are separate.
- A source must not be described as approved until a named human reviewer records an explicit decision against the exact release and files.
- A corpus preparation success or checksum match proves reproducibility/integrity only; it does not establish copyright, privacy, or model-training permission.
- The deterministic sample-review.json emitted by the Wikimedia pipeline is a review queue, not a completed review. Every sample needs a human decision, date, reviewer, and notes.
- Keep source archives, full corpus, credentials, and restricted files out of Git. Do not publish corpus artifacts unless the exact source terms and access policy allow it.
- No full model training starts while the source register has no approved source and the actual corpus manifest does not match reviewed files.

## Sign-off (must be completed by a human)

- Reviewer name/role: PENDING
- Review date (UTC): PENDING
- Exact release and SHA-256 values checked: PENDING
- Training-use decision and rationale: PENDING
- Raw-data retention/distribution decision: PENDING
- Model-weight distribution decision and rationale: PENDING
- Attribution/share-alike implementation reviewed: PENDING
- Privacy and sampled-content review completed: PENDING
- Legal reviewer, if required: PENDING

Do not replace pending values with inferred or generated approval.

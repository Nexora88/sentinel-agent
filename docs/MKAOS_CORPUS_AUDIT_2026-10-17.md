# MKAOS Corpus Audit — 2026-10-17

## Status and scope

This is an evidence-limited technical audit note for the local repository state and GitHub Actions run #11. It is not a legal opinion, source licence approval, or claim that the Wikimedia sample queue has been reviewed.

- Repository: `Nexora88/sentinel-agent`
- Wikimedia workflow run: [39060373225](https://github.com/Nexora88/sentinel-agent/actions/runs/39060373225)
- Run head SHA: `4afd4fdcbfbe4d683b893d76aa1a337590f87caf`
- Pinned candidate: Turkish Wikipedia dump `trwiki-20260901-pages-articles-multistream.xml.bz2`
- Last checked state: workflow `in_progress`; preparation step still running; report artifact not yet present.
- The workflow's manual full-corpus retention input was not enabled. This audit did not download or publish the full corpus.

## Evidence currently available

1. The Wikimedia workflow unit-test step passed.
2. The dump and the release-specific upstream MD5 list were downloaded successfully.
3. Checksum verification and corpus preparation were still running at the last status check. Therefore, actual archive SHA-256, selected output hashes, record counts, and `sample-review.json` contents are not yet available for this audit.
4. `data/mkaos/source-register.json` explicitly has `current_approved_sources: []`, `corpus_ready: false`, and `model_training_allowed: false`. These values must remain unchanged until source-specific human review is documented.
5. The training workflow requires a private self-hosted runner with labels `mkaos-training,gpu,ram-16g`, a valid approval reference, approved corpus/manifest paths, a working accelerator, and at least 10 GiB free at `/opt/mkaos-private-checkpoints`. Runner availability has not been verified.

## Technical review of the Wikimedia preparation pipeline

### Strengths observed in source

- Pins a dated release rather than a moving `latest` alias.
- Checks the archive against the official release MD5 list and records SHA-256 hashes for the archive and output splits.
- Uses streaming XML parsing and removes processed page elements from the parse tree.
- Keeps page/revision IDs, timestamps, titles, article URLs, attribution guidance, and license notes in each record.
- Applies Unicode NFC normalization, common email/phone-like masking, length limits, and exact normalized-text deduplication.
- Splits by page ID, so a page is not split across train/validation/test.
- Generates a deterministic review queue with pending decisions; the queue is not represented as a completed review.
- Defaults to uploading the report only. Full corpus artifact retention requires a separate manual opt-in and was not requested here.

### Known limitations / risks

- Email/phone pattern masking is not comprehensive PII or sensitive-content detection. Living-person biographies, addresses, identifiers, private details, defamatory material, and other sensitive content may remain.
- Exact deduplication does not catch near-duplicates, paraphrases, copied external text, or source/document overlap beyond exact normalized text.
- Page-level split avoids same-page leakage, but does not guarantee independence between related pages, translated copies, templates, or mirrored content.
- Wikitext cleanup is not a copyright clearance process. Imported text, quoted material, images/media omitted from the text, article-level exceptions, and applicable licence versions still need review.
- Attribution text points to article history, but the legal/technical sufficiency of downstream attribution and share-alike implementation has not been established.
- The pipeline's automated tests cover deterministic split behavior, approximate ratios, exact duplicate digest behavior, simple email/phone masking, hash function correctness, and basic Turkish Unicode cleanup. These tests do not establish corpus quality, legal permission, or PII safety.

## Review of the existing first-party 12-record smoke corpus

Files examined: `data/mkaos/first-party-smoke-v1.jsonl`, `data/mkaos/first-party-smoke-v1.manifest.json`, and `docs/MKAOS_FIRST_PARTY_CORPUS_REVIEW.md`.

- The JSONL contains 12 short Turkish diagnostic records: 4 train, 4 validation, 4 test.
- Topics are narrowly concentrated on software testing, model training, hashes, data handling, and Python/Rust checkpoint compatibility.
- The visible text records contain no obvious direct personal contact information or secrets. This is a small manual surface check, not a full automated scan or formal privacy clearance.
- The records are concise and generally understandable Turkish, but they are synthetic/AI-assisted draft diagnostics rather than a representative language corpus. They cannot support claims about general-purpose Turkish capability.
- Four test records are not statistically meaningful for an independent quality claim; this set is only suitable for a pipeline smoke test if its rights/use gate is legitimately approved.
- A direct local SHA-256 recomputation over each JSONL record's UTF-8 `text` field was run against all 12 manifest entries. **All 12 computed hashes differed from the recorded `sha256` values.** The 12 sample IDs were unique and split counts were 4/4/4. The basic automated scan found no email-like strings, URLs, or 8+-digit runs in these 12 short records.
- This hash mismatch is a blocking provenance defect. Do not silently overwrite hashes or treat revision 1 as verified. Determine whether the manifest was generated from earlier text, uses a different documented canonicalization rule, or contains stale hashes; then create a new revision with the exact hashing rule and a recorded correction. The existing review document's pending status still applies.

### Material documentation inconsistency

The manifest currently labels each record `human_review: approved` and `pii_status: cleared`, while `docs/MKAOS_FIRST_PARTY_CORPUS_REVIEW.md` says human maintainer review is pending and explicitly instructs maintainers not to change those fields just to pass validation. The manifest also says `license_reviewed: false` and the proposed CC0 label remains unapproved.

**Resolution required:** a maintainer must reconcile these contradictory statements against the actual review history. Do not infer legal approval from the project owner's local experiment authorization or from this automated audit. Until reconciled, treat human content review, privacy clearance, and license review as unresolved and keep the general training gate closed.

## Source / attribution / rights status

- The Wikimedia candidate remains blocked pending source-specific rights, attribution/share-alike, imported-content, privacy, and weight-distribution review.
- The exact downloaded archive hash and output hashes must come from the completed run's manifest; they must not be guessed or copied from another release.
- Any human reviewer should record reviewer identity/role, UTC date, exact release and file hashes, evidence URLs, attribution obligations, training-use decision, raw-data redistribution decision, model-weight distribution decision, and rationale.
- Training-use permission and permission to distribute model weights are separate decisions.
- The current source register correctly has no approved sources and disallows training. This audit does not change that status.

## Required follow-up once the report artifact exists

1. Download only `mkaos-wikimedia-corpus-report`; do not download the full corpus artifact.
2. Verify the manifest's release, archive size, upstream checksum, SHA-256 values, split counts, filtering counts, and output byte sizes.
3. Inspect all deterministic sample candidates from train/validation/test privately. Record a decision, reviewer, UTC date, and notes for each sample. Check the prepared record against its source page.
4. Run explicit detectors for email, phone, postal address, identifiers, credentials/secrets, sensitive personal details, and unsafe content; manually inspect flagged cases and a random sample. Report detector limitations and false positives.
5. Assess Turkish text quality, markup residue, language drift, empty/low-information text, duplicate and near-duplicate rates, and cross-split source/document leakage. Preserve the independent test split from model tuning.
6. Update the rights dossier only with evidence. Do not set `permitted_use_now`, `corpus_ready`, or `model_training_allowed` to true until an authorized human has made and documented the decision.
7. Before any training, verify the private GPU runner, storage, CUDA/ROCm, and approved exact corpus/manifest hashes. After a legitimately approved run, test checkpoint reload, Python/Rust parity, and a separately frozen independent Turkish evaluation set.

## Current conclusion

**BLOCKED — waiting for completed Wikimedia report and human rights/privacy review.** No Wikimedia examples are claimed reviewed, no training has been started, no checkpoint has been created, and no independent model performance result is available.

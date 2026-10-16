# MKAOS Turkish Wikimedia corpus: reproducible preparation

## Scope and current decision

This pipeline pins the official Turkish Wikipedia XML article dump release **20260901** and creates UTF-8 JSONL training, validation, and document-level test splits. It records a local SHA-256 for the compressed archive and each selected output file, verifies the archive against Wikimedia's published MD5 list when supplied, and retains per-record title, page/revision IDs, timestamp, article URL, license notice, and attribution guidance.

**Prepared does not mean legally approved.** The initial status remains `prepared_pending_human_rights_privacy_and_content_review`. The source registry must not mark this source approved and `model_training_allowed` must remain false until the project records a source-specific human review. Model-weight redistribution is a separate decision and remains unapproved.

## Pinned source

- Project: Turkish Wikipedia, Wikimedia public dump service.
- Release: `20260901` (do not use the moving `latest` alias in a reproducible run).
- Archive: `trwiki-20260901-pages-articles-multistream.xml.bz2`
- Exact archive URL: `https://dumps.wikimedia.org/trwiki/20260901/trwiki-20260901-pages-articles-multistream.xml.bz2`
- Official dump index: `https://dumps.wikimedia.org/trwiki/latest/`
- Official dump documentation: https://meta.wikimedia.org/wiki/Data_dumps
- Wikimedia license/reuse terms: https://meta.wikimedia.org/wiki/Terms_of_use/Creative_Commons_4.0/en

The workflow downloads the release-specific `trwiki-20260901-md5sums.txt` file and verifies its published MD5 entry. MD5 is used only for upstream transport-integrity compatibility; SHA-256 is independently calculated and recorded for the archive and each output split. The generated manifest contains the actual hashes from the run; hashes are not guessed or committed before the file is downloaded.

## Cleaning and filtering

1. Parse the XML stream incrementally; retain only main-namespace pages with a current revision.
2. Skip redirects and titles explicitly marked as disambiguation pages.
3. Strip MediaWiki markup using the pinned `mwparserfromhell` parser; remove residual references, HTML tags, tables, URLs, and category markup.
4. Normalize extracted text to Unicode NFC and normalize whitespace. This is corpus cleaning and does not change the MKAOS tokenizer's own normalization contract.
5. Mask common email addresses and phone-like sequences. This is only a basic risk reduction, not comprehensive PII or sensitive-content detection.
6. Reject text shorter than 300 characters or longer than 200,000 characters.
7. Remove exact duplicate cleaned texts using a SHA-256 over NFC, collapsed whitespace, and case-folded content. Near-duplicates, paraphrases, mirrored content, and copied material from external sites are not comprehensively detected.
8. Assign whole pages to train/validation/test using a deterministic SHA-256 bucket of page ID: 90% / 5% / 5%. Documents are never split across sets. This is a document-level holdout from one source, not an independent external-source benchmark.

## Output schema

Each JSONL row contains `record_id`, `source_id`, `source_release`, page/revision identifiers and timestamp, title, article URL, cleaned-text SHA-256, split, text, attribution guidance, and license notice. The `corpus-manifest.json` records source URL, release, archive size and checksums, software versions, filtering counts, per-split row counts, byte sizes, SHA-256 values, and pending review statuses.

## Rights, attribution, privacy, and quality review checklist

Before training on this source, a human reviewer must:

- Confirm the actual release and the per-file licensing terms; the general Wikimedia terms are not a substitute for article-level exceptions or imported content.
- Review CC BY-SA/GFDL applicability, required attribution and share-alike duties, and how these duties will be met for any redistributed dataset or downstream use.
- Decide whether the planned training use is permitted and document the evidence URL, review date, reviewer, and exact release/hash.
- Review privacy and sensitive content risks, including living-person biographies, personal information, harmful/defamatory claims, and content not suitable for a general-purpose assistant. The email/phone masker is not enough.
- Review copyright exceptions, templates, quotations, and externally imported material; automated wikitext stripping does not resolve rights.
- Validate deduplication quality and inspect samples from each split.
- Keep training, validation, and test sets isolated by page/document. Do not tune against the test split.
- Approve model-weight redistribution separately. Even if internal training is allowed, do not publish a checkpoint or claim that the weights are cleared until that separate review is complete.

## Reproduce locally

Python 3.11+ is recommended. Install `requirements-corpus.txt` and download the pinned archive and the same release's MD5 list into a directory with enough free space. The raw compressed archive is about 1.14 GB; allow several additional GB for extracted JSONL splits and temporary files.

```powershell
python -m pip install -r requirements-corpus.txt
$release = "20260901"
$base = "https://dumps.wikimedia.org/trwiki/$release"
New-Item -ItemType Directory -Force data\wikimedia\raw, data\wikimedia\prepared | Out-Null
Invoke-WebRequest "$base/trwiki-$release-pages-articles-multistream.xml.bz2" -OutFile "data\wikimedia\raw\trwiki-$release-pages-articles-multistream.xml.bz2"
Invoke-WebRequest "$base/trwiki-$release-md5sums.txt" -OutFile "data\wikimedia\raw\trwiki-$release-md5sums.txt"
python scripts/mkaos/prepare_wikimedia_corpus.py --archive "data\wikimedia\raw\trwiki-$release-pages-articles-multistream.xml.bz2" --upstream-md5-file "data\wikimedia\raw\trwiki-$release-md5sums.txt" --output-dir "data\wikimedia\prepared"
```

The CI workflow runs the same process on a hosted runner and publishes a short-lived artifact containing the prepared splits and manifest for inspection. It does not train a model or publish weights. Treat all output as unapproved until the checklist above is completed.

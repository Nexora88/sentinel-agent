# MKAOS Turkish Wikipedia corpus preparation evidence — 2026-10-16

This record captures the successful pinned-dump preparation run already present in GitHub Actions. It is reproducibility evidence only. It is **not** a human rights decision, content quality approval, or permission to train/distribute weights.

- Workflow run: [MKAOS Wikimedia corpus preparation #7](https://github.com/Nexora88/sentinel-agent/actions/runs/38905291295)
- Run status: success
- Workflow job: Download, verify, clean, deduplicate, and split pinned Turkish Wikipedia dump
- Job ID: 116987566137
- Pinned source release: Turkish Wikipedia dump 20260901
- Dataset ID: mkaos-trwiki-20260901-cleaned-v1
- Archive: trwiki-20260901-pages-articles-multistream.xml.bz2
- Archive size: 1,129,722,504 bytes
- Archive SHA-256: 059c4d3be42b388734efceba08b5f933ddb1b4412b3f5c12f9e7c53a42b353af

## Prepared split outputs

| Split | Documents | Bytes | SHA-256 |
|---|---:|---:|---|
| Train | 427,086 | 1,545,627,994 | 244d60a18ca3401d6578220391865523bcc7e08ae2d3698f4df08d71850e7954 |
| Validation | 23,772 | 86,051,981 | 0a7fb8a034474b5e97c38e5e96cf4a7999ac6c3f50d7abbaadc3d202f4330d0f |
| Independent test | 23,640 | 85,016,775 | a241673efe01c76ad3b515cb697767615e11361a33414fa207f41953aee84857 |
| **Total retained** | **474,498** | **1,716,696,750** | Per-split hashes above |

The parser saw 1,655,146 XML pages and retained 1,238,380,721 text characters. It recorded 613,935 email/phone-like redaction events across 97,398 documents. Filters recorded 621,106 non-main-namespace/missing-revision exclusions, 280,997 too-short exclusions, 272,651 redirects, 5,866 disambiguation pages, 24 too-long documents, and 4 exact duplicate texts. Contact masking is not comprehensive PII or sensitive-content review.

## Artifact and retention

The run uploaded the small machine-readable manifest/report artifact only:
- [Run report artifact](https://api.github.com/repos/Nexora88/sentinel-agent/actions/artifacts/12051099721)
- Artifact SHA-256: 61600419f36433ff4473a348e45f33fde742e7efb4e966dfa9f263bba791cc57
- Full corpus artifact retention was skipped, as intended. The full prepared JSONL files are not committed to Git and are not present in this repository artifact.

## Human review status

- Training rights: **PENDING HUMAN REVIEW**
- Privacy/sensitive content: **PENDING HUMAN REVIEW**
- Attribution/share-alike implementation: **PENDING HUMAN REVIEW**
- Model-weight redistribution: **NOT APPROVED**
- Sample review: **NOT COMPLETED in workflow run #7**. That run predates the bounded deterministic sample-review queue added in PR #68. Rerun the updated workflow to create sample-review.json, then have a human reviewer fill in each decision and record reviewer/date/notes.
- Production training permitted: **NO**

The archive checksum and split hashes establish file identity and reproducibility; they do not grant training rights. Do not feed this corpus to a full training run until the exact files, sample review, privacy, attribution, and model-weight implications receive a documented human decision.

# MKAOS Human Review and GPU Gate Record

**Status: TEMPLATE ONLY — NO SOURCE OR TRAINING APPROVAL GRANTED**

This document is an evidence-capture template. Automated tests, checksums, public availability, a project owner's request, or a completed data-cleaning run do not constitute legal, privacy, or model-weight-distribution approval. Do not change `data/mkaos/source-register.json` approval flags until a qualified human reviewer records a source-specific decision and the required evidence is attached.

## 1. Review record metadata

- Review ID:
- Review date (UTC):
- Reviewer name / role:
- Second reviewer / counsel (if applicable):
- Exact repository commit reviewed:
- Intended training run / model:
- Intended model-weight distribution (private only / public / other):
- Decision status: `PENDING` / `APPROVED WITH CONDITIONS` / `REJECTED`
- Evidence location (private, access-controlled; do not put confidential correspondence or personal data in the public repo):

## 2. Required source-by-source decisions

Complete one full section for every source and exact release. Do not infer approval for one source from another source's review.

### A. Wikimedia / Turkish Wikipedia

- Source ID: `wikimedia-turkish-wikipedia`
- Exact dump/release and retrieval date:
- Official checksum evidence and locally calculated SHA-256:
- Files/pages included and exclusions:
- License(s) and evidence for the exact content scope:
- Imported-content, page-level exceptions, and third-party material checked:
- Attribution / author-credit / modification-notice plan:
- ShareAlike / adaptation / database-right analysis, including whether and how the obligations could affect the trained model or redistributed weights:
- Privacy, personal data, sensitive content, and removal-request handling:
- Intended training use permitted? Evidence:
- Intended model-weight distribution permitted? Evidence and conditions:
- Human content/sample review evidence:
- Decision and rationale:
- Reviewer signature/identity and date:
- Conditions, unresolved issues, and re-review trigger:

### B. Mozilla Common Voice Turkish sentence text

- Source ID: `mozilla-common-voice-text`
- Exact product/release, dataset ID, authorized download route, and retrieval date:
- Original archive SHA-256 and selected text-file SHA-256:
- Exact files/columns retained; confirm audio, client IDs, and unnecessary speaker metadata are excluded:
- Dataset license and no-redistribution restrictions evidenced for this exact release:
- Upstream provenance and rights review for each source category (including Wikipedia, sentence collector, SETimes, and Other):
- Attribution obligations, if any:
- Privacy / personal data / consent and retention analysis:
- Intended training use permitted? Evidence:
- Intended model-weight distribution permitted? Evidence:
- Human content/sample review evidence:
- Decision and rationale:
- Reviewer signature/identity and date:
- Conditions, unresolved issues, and re-review trigger:

### C. Tatoeba Turkish text

- Source ID: `tatoeba-turkish-text`
- Exact export/version, retrieval date, file list, and SHA-256:
- Sentence-level licenses/exceptions and contributor attribution mapping:
- Confirm Turkish rows are covered by the asserted license; do not infer from another language subset:
- Attribution retention and model/data notices:
- Audio excluded unless separately reviewed and licensed:
- Privacy / personal data review:
- Intended training use permitted? Evidence:
- Intended model-weight distribution permitted? Evidence:
- Human content/sample review evidence:
- Decision and rationale:
- Reviewer signature/identity and date:
- Conditions, unresolved issues, and re-review trigger:

### D. HPLT Turkish cleaned text

- Source ID: `hplt-v2-turkish-cleaned`
- Exact release, package/file subset, retrieval date, size, and SHA-256:
- Packaging license versus underlying-text rights distinguished and evidenced:
- Source/document provenance, restrictions, and exclusion rules:
- Attribution obligations:
- Privacy, personal data, secrets, and sensitive-content review:
- Intended training use permitted? Evidence:
- Intended model-weight distribution permitted? Evidence:
- Human content/sample review evidence:
- Decision and rationale:
- Reviewer signature/identity and date:
- Conditions, unresolved issues, and re-review trigger:

### E. Additional or first-party sources

Create a separate section for each additional source, including exact version, ownership/authority, provenance, applicable license/terms, privacy checks, attribution, ShareAlike/adaptation analysis, training-use permission, model-weight distribution permission, reviewer evidence, decision, and conditions. Synthetic or first-party authorship claims do not waive privacy or third-party-content checks.

## 3. Corpus-level gate (complete only after every included source is decided)

- Included source IDs and exact release IDs:
- Manifest path/version and SHA-256:
- Corpus SHA-256 and selected-file hashes:
- Record counts by train / validation / independent test:
- Duplicate and near-duplicate filtering results:
- PII / secrets / sensitive-content scan results and human triage:
- Source/document-level leakage check:
- Sample-review queue: number reviewed, number pending, rejected/removed counts:
- Attribution/provenance records retained:
- Data retention and deletion procedure:
- Final corpus decision, rationale, reviewer identity, date:
- Model-training permission explicitly granted? `YES` / `NO`
- Model-weight redistribution permission explicitly granted? `YES` / `NO` / `CONDITIONAL`
- Exact conditions and distribution scope:

**Gate rule:** unless all included sources have a documented positive decision for the intended use, keep `current_approved_sources: []`, `corpus_ready: false`, and `model_training_allowed: false`. Do not mark a source approved solely because automated checks pass.

## 4. Private Linux GPU runner acceptance record

Runner registration must be performed by an authorized repository administrator on a trusted, private Linux x64 machine. Do not register an untrusted/shared host or expose runner registration tokens in logs, chat, source control, or artifacts.

- Host owner / administrator:
- Host inventory ID and private network/security controls:
- Linux distribution/version and x86_64 confirmation:
- Runner version and registration date:
- Registered repository scope and runner group:
- Required labels confirmed: `self-hosted`, `linux`, `x64`, `mkaos-training`, `gpu`, `ram-16g`
- Runner is online and eligible for this repository/environment? Evidence:
- Environment `mkaos-training-approved` protection/reviewer settings checked? Evidence:
- GPU model and driver:
- PyTorch version and `torch.cuda.is_available() == true` result:
- Accelerator device detected and usable in a minimal smoke test? Evidence:
- RAM available / total; at least the workflow's `ram-16g` label is truthful:
- `/opt/mkaos-private-checkpoints` exists, is writable by the runner service account, is on the intended volume, and has at least 10 GiB free:
- Checkpoint permissions, encryption/access controls, backup and retention policy:
- Runner logs/artifacts confirmed not to include corpus contents or model weights:
- Acceptance decision, operator, and date:

**Runner gate rule:** if any label, actual accelerator, write permission, or free-space check fails, do not dispatch training. The label alone is not proof of hardware.

## 5. Training dispatch authorization

Fill only after sections 2–4 have passed and the source register reflects the independently documented decision.

- Human review ID (must link to actual evidence):
- Approved source IDs and exact versions:
- Approved manifest path and SHA-256:
- Approved private corpus path and SHA-256:
- Source register commit SHA:
- GPU runner acceptance record ID:
- Checkpoint volume free space at dispatch (GiB):
- Model profile/config reviewed:
- Checkpoint privacy/retention plan:
- Training run ID (after dispatch):
- Dispatch authorized by / date:
- Post-run report reviewed by / date:

**Current known gate state (last checked 2026-10-17):** the repository source register has no approved sources; `corpus_ready` and `model_training_allowed` are false. A prior repository-level runner inventory returned zero self-hosted runners. Therefore training remains blocked until new evidence changes those facts. This statement must be rechecked before any future dispatch.

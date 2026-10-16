# MKAOS — public open-source status

**Project intent:** develop an auditable, Turkish-first local AI runtime and, over time, a model trained from sources whose use is documented and approved.

## Public development policy

MKAOS is published for worldwide inspection, use, contribution, and independent evaluation under the repository's MIT license, subject to the actual contents of each file and any separately licensed third-party component. No institutional endorsement, certification, or official approval is claimed.

- The repository's `LICENSE` file is the controlling license notice for this project source.
- Third-party model weights, datasets, tokenizer assets, voices, and other bundled/downloaded materials may have separate terms. Their licenses do not become MIT merely because this repository is MIT-licensed.
- Public availability is not proof that a dataset permits model training, redistribution, or commercial use.
- Keep private data, unreviewed archives, credentials, local hash manifests, and private review evidence out of public commits unless publication is explicitly cleared.
- Preserve attribution, notices, provenance, and required license texts for all accepted dependencies and data.
- Report security issues responsibly; do not publish secrets or private training data in issues or pull requests.

## Evidence-first status (2026-10-16)

| Area | Evidence / status |
|---|---|
| Source repository license | MIT notice exists in `LICENSE` |
| Host profile | Offline OS/architecture metadata helper and tests |
| CI host coverage | Windows, macOS, Linux; Python 3.11/3.12 portability jobs |
| ARM64 CI | Ubuntu ARM64 portability and source-gate tests passed in the PR workflow |
| Source register | Schema/consistency validator merged; empty register remains zero approved sources |
| Source archive hashes | Local SHA-256 inventory tool exists; it must be run against the actual local files |
| Approved training corpus | **Not ready** — no approved sources are currently recorded |
| MKAOS-owned trained checkpoint | **Not demonstrated** — do not describe synthetic CI training as a trained model |
| Cross-platform native model inference | **Not certified** — Python host tests do not prove Rust/model compatibility on every platform |
| Official certification / endorsement | Not claimed or required for public development |

Passing CI demonstrates only the specific checks and environments in that workflow. It does not certify all CPU architectures, accelerators, devices, model quality, legal compliance, or security.

## Before training an owned model

1. Obtain the exact source archives from their authoritative locations.
2. Record version/snapshot, acquisition time, source URL, license evidence, training and redistribution permissions, privacy review, reviewer reference, and decision in the source register.
3. Generate and verify SHA-256 inventories from the actual local files. Never invent or pre-fill hashes.
4. Quarantine sources with unclear terms, personal data, or missing permissions.
5. Prepare a reproducible, deduplicated training corpus only from approved sources; record its manifest hash, split policy, seed, environment, and training logs.
6. Train from initialized weights, save a real checkpoint, and verify checkpoint hashes and round-trip loading.
7. Evaluate on a held-out Turkish benchmark and run reference-parity, safety, memory, latency, tokens/second, and stability tests.
8. Publish only artifacts whose redistribution terms are cleared, with a model card and provenance report.

The validator is a technical guardrail, not a lawyer or an independent evidence verifier. A filled record is not automatically true just because it passes schema validation.

## Contributions

Use focused pull requests with tests and documentation. State what was actually tested, include reproducible commands, disclose third-party code/data, and avoid unsupported claims such as “fully sovereign,” “trained from scratch,” or “works on every device.” CI must pass before merging. Keep main usable and leave unverified hardware/accelerator support marked as unverified.

## Public project statement

MKAOS welcomes worldwide inspection and contributions. Its ambition is a locally runnable, Turkish-first, increasingly independent AI stack. Independence will be claimed incrementally, only when source provenance, training permission, owned weights, runtime parity, offline behavior, and quality/performance results have reproducible evidence.

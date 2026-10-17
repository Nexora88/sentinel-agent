# MKAOS technical skills data plan

## Goal

Build measurable capability in three distinct tracks rather than treating general Turkish text as sufficient:

1. **Software engineering:** explain code, generate small changes, write tests, debug, refactor, document APIs, and review diffs across Python, JavaScript/TypeScript, Rust, SQL and shell.
2. **Defensive cybersecurity:** secure code review, threat modeling, input validation, authentication/authorization, secrets hygiene, dependency auditing, logging, incident triage and remediation. Use intentionally vulnerable training labs only in isolated, authorized environments; do not train the model to assist unauthorized access.
3. **Turkish technical communication:** answer in Turkish, preserve exact technical terms, explain trade-offs, ask for missing context, and cite repository/file evidence when tools are used.

## Data-source first step: CodeSearchNet

- Official repository: https://github.com/github/CodeSearchNet
- Official archive pattern documented by its maintainers: https://s3.amazonaws.com/code-search-net/CodeSearchNet/v2/{language}.zip
- Coverage documented by maintainers includes Python, JavaScript, Java, Go, Ruby and PHP.
- The dataset contains source code from many repositories; the maintainers describe per-repository license information in the downloaded `*_licenses.pkl` files. A single blanket license must not be assumed.
- This project’s workflow downloads one selected language archive in a temporary runner, verifies ZIP structure and records a SHA-256 and file inventory. It uploads **only the provenance report**, never the raw dataset, and deletes the downloaded archive at the end.
- The generated hash is calculated after download; it proves internal report consistency, not authenticity against an independent upstream checksum.
- Status remains **BLOCKED for training** until human review covers source-level licenses, provenance, privacy/PII, attribution/ShareAlike and whether trained-weight distribution is permitted.

## Training and evaluation chain

1. Acquire a source into an isolated temporary workspace.
2. Record origin URL, retrieval time, archive SHA-256, version/commit and file inventory.
3. Review license and provenance at source/repository level; quarantine unclear sources.
4. Scan for secrets, personal data, generated/vendor/build files and duplicated examples.
5. Normalize and deduplicate; keep source attribution and license metadata alongside every retained record.
6. Create repository-separated train/validation/test splits to avoid leakage.
7. Human-review a sample and record reviewer, date, decision and evidence.
8. Only then request approval to add the source to the approved-source register.
9. Train only on the private approved corpus; keep corpus and weights out of the public Git history unless their redistribution rights are explicitly cleared.
10. Evaluate on held-out tasks, with reproducible code tests and defensive security benchmarks.

## Initial evaluation suites (not training data)

- Code generation: unit tests, type checks, lint, and patch correctness.
- Code understanding: explain functions, identify invariants, trace data flow and summarize dependencies.
- Defensive security: find hard-coded secrets, SQL injection risk, path traversal, unsafe deserialization, missing authorization, weak input validation and vulnerable dependencies; then produce safe patches and regression tests.
- Safety: refuse requests to break into third-party systems, steal credentials, evade detection, or deploy malware; redirect to authorized defensive testing.
- Turkish quality: technical terminology, accuracy, uncertainty handling and concise explanations.

## Repository policy

Never commit raw multi-gigabyte datasets, model weights, secrets, credentials or unreviewed third-party source. Store approved data in private controlled storage and keep only manifests, source/license decisions, preprocessing code, evaluation definitions and non-sensitive reports in Git. Do not automatically connect a downloaded source to the training workflow.

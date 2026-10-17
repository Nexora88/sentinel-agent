# MKAOS First-Party Corpus Review and Training Gate

Status: **PENDING HUMAN MAINTAINER REVIEW — TRAINING BLOCKED**

Dataset: `data/mkaos/first-party-smoke-v1.jsonl`  
Manifest: `data/mkaos/first-party-smoke-v1.manifest.json`  
Current dataset revision: `2`

## Current facts

- 12 AI-assisted Turkish diagnostic samples are present (4 train, 4 validation, 4 independent test).
- Revision 2 recomputes all 12 per-record SHA-256 values over the exact UTF-8 bytes of each JSONL `text` field (excluding JSON wrapper and newline); an automated recheck found 12/12 matches.
- Every record is explicitly marked `human_review=pending` and `pii_status=pending_review`; this is not a privacy clearance.
- No third-party corpus text was intentionally copied and no personal data is intended; these statements still require review.
- The proposed `CC0-1.0` label is **not approved**; `license_reviewed=false` remains.
- The previous manifest revision had contradictory approved/cleared flags and mismatching hashes. Revision 2 records a transparent correction; it does not approve training.
- No training run, checkpoint hash, or Rust inference benchmark is claimed by this document.

## Human maintainer review checklist

A maintainer must verify each item against the actual corpus and intended use. If any answer is unknown, keep the gate closed.

- [ ] I reviewed every record in the JSONL corpus and confirmed the exact text is present and suitable.
- [ ] I verified the authorship/origin of each record, including the role of AI assistance, and have authority to use it for model training.
- [ ] I chose and verified the applicable license/terms; the proposed CC0 label is not accepted by default.
- [ ] I reviewed privacy/PII and confirmed no personal or confidential information is included.
- [ ] I confirmed whether the checkpoint and derivatives may be shared. Until explicitly cleared, outputs remain local and non-redistributable.
- [ ] I verified the manifest hashes and that train, validation, and independent test splits do not overlap.
- [ ] I accept that this tiny corpus is only a pipeline smoke test and cannot establish general-purpose Turkish language capability.

### Decision record — fill only after review

- Reviewer identity/role:
- Review date (UTC):
- Corpus revision and manifest SHA-256:
- Authorship and publication-rights decision:
- Selected license/terms and evidence:
- Privacy/PII decision:
- Checkpoint distribution decision:
- Approved scope: `local-only experiment` / `training and distribution` / `rejected`
- Notes or evidence links:

Do not use an unchecked or blank decision record as approval. Do not claim legal certainty based only on this checklist.

## After approval: run the gated smoke test

Run from the repository root in a controlled local environment with a compatible Python and PyTorch installation. This corpus is intentionally too small for meaningful language-model capability claims; use a short sequence length only to exercise the pipeline.

1. Only after a human decision is documented, update each reviewed record's `human_review` and privacy status to reflect the actual decision, and record the actual reviewed license decision. Set `license_reviewed=true` only if that review really occurred. Do not bulk-approve records.
2. Ensure the source register authorizes the exact local-only dataset; do not approve third-party sources by implication.
3. Validate the manifest and source gate. A failing gate means **do not train**.
4. Run the random-initialization trainer in local-only mode with a short smoke-test configuration, for example:

   ```bash
   python tools/train_mkaos_from_scratch.py \
     --corpus data/mkaos/first-party-smoke-v1.jsonl \
     --manifest data/mkaos/first-party-smoke-v1.manifest.json \
     --source-register data/mkaos/source-register.json \
     --output-dir ./artifacts/mkaos-smoke \
     --experimental-local-only \
     --epochs 1 --batch-size 1 --sequence-length 16 \
     --hidden-size 32 --layers 1 --heads 4 --kv-heads 2 \
     --intermediate-size 64
   ```

   This command is a proposed smoke-test configuration, not a recorded run. It may still fail if the dataset has insufficient tokens or the environment lacks dependencies.

5. Capture the training report, checkpoint SHA-256, seed, device, loss metrics, and exact source revision. Do not commit generated weights by default.
6. Load that exact checkpoint in the Rust engine using its reported SHA-256. Record the Rust command, runtime, generated token count, tokens/second, and errors.
7. Compare Python and Rust outputs/logits where the existing parity harness supports it. A successful load alone is not proof of equivalent generation or model quality.
8. Report the result as a **tiny experimental from-scratch pipeline smoke test**, not as a trained general-purpose language model.

## Results — intentionally unfilled

- Human rights review: **PENDING**
- Random-init training: **NOT RUN**
- Checkpoint SHA-256: **NOT AVAILABLE**
- Rust load/measurement on trained weights: **NOT RUN**
- General-purpose model claim: **NOT JUSTIFIED**

# MKAOS Research Tracks and Data Governance

This roadmap separates source auditing, educational modules, simulation work, and any future training. Passing tests or producing a source-audit report does **not** authorize training.

## Track 0 — Source audit and governance
- Pull request: https://github.com/Nexora88/sentinel-agent/pull/78
- Run the manual workflow `.github/workflows/mkaos-technical-skills-audit.yml` for one language at a time.
- Inspect the JSON report's archive byte count, SHA-256, ZIP entry count, source URL, and review flags.
- The computed SHA-256 is an integrity fingerprint of the retrieved file, not proof of upstream authenticity unless compared with an independently published trusted checksum.
- Do not add CodeSearchNet to the approved-source register until repository-level licenses, provenance, privacy, attribution/ShareAlike, and model-weight distribution terms have been reviewed by a human.
- Upload only the report artifact; never upload the raw corpus through this workflow.

## Track 1 — Defensive cybersecurity
Issue: https://github.com/Nexora88/sentinel-agent/issues/79
- Use secure coding, threat modeling, dependency hygiene, synthetic log analysis, and owned/local labs.
- Add unit tests for validation, secret redaction, safe defaults, and authorization boundaries.
- No third-party exploitation or credential theft.

## Track 2 — Atatürk and Republic knowledge
Issue: https://github.com/Nexora88/sentinel-agent/issues/80
- Prioritize official archives, TBMM publications, Atatürk Araştırma Merkezi, and clearly identified public-domain material where reuse terms are confirmed.
- Every record needs source URL, edition/date, retrieval date, rights note, and review state.
- Separate verified facts from interpretation; test citations and key dates.

## Track 3 — Civil radar and signal-processing simulation
Issue: https://github.com/Nexora88/sentinel-agent/issues/81
- Generate synthetic data with fixed random seeds.
- Test noise generation, filtering, numerical bounds, uncertainty labels, and deterministic output.
- Keep the use cases civil and educational: weather, aviation safety concepts, search-and-rescue, and disaster monitoring.
- Exclude weapon targeting, fire-control, and operational battlefield tracking.

## Track 4 — Visual reasoning and simulation benchmark
Issue: https://github.com/Nexora88/sentinel-agent/issues/82
- Begin with self-generated diagrams, synthetic maps, toy physics, and civil weather/disaster scenarios.
- Store creator/source, license, SHA-256, version, seed, expected result, and review status.
- Upload small previews and benchmark reports only where rights allow; avoid bulk third-party image uploads.

## Release gates
1. Tests pass.
2. Provenance and license metadata are complete.
3. Human reviewer records source-level approval.
4. Only explicitly approved sources may enter preparation/evaluation.
5. Training remains blocked until the separate training authorization and hardware gates are satisfied.

## Current status
No source is approved for model training. No model training is authorized by this roadmap.

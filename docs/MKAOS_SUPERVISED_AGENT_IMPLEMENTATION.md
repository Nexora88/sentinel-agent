# MKAOS supervised coding agent and location services

## Implemented in this change

- `core/location_data_adapters.py`: provider-injected weather and traffic adapter contracts. They require explicit location consent, validate coordinates, timestamp results, and label cached results `cached` or `stale` after the freshness threshold. No provider is silently selected and no network call happens unless a provider fetcher is configured.
- `tools/mkaos_supervised_coding_agent.py`: accepts an explicit unified-diff patch, validates it in a detached Git worktree, and runs fixed compile/test/diff checks. It refuses a dirty source checkout and does not execute commands supplied by the patch, push a branch, open a PR, or merge.
- `tools/mkaos_private_security_report.py`: writes redacted findings to a local file with restrictive permissions where supported. It never creates a GitHub issue or publishes findings.
- `config/mkaos-product-tiers.json`: records the product policy: local/free/no account by default; team/self-hosted capabilities are a future tier; billing and account enforcement are explicitly marked not implemented.

## Validation commands

```bash
python -m unittest discover -s tests -p 'test_location_data_adapters.py' -v
python -m unittest discover -s tests -p 'test_private_security_report.py' -v
python -m unittest discover -s tests -p 'test_mkaos_supervised_coding_agent.py' -v
```

For supervised patch validation, from a clean local clone:

```bash
python tools/mkaos_supervised_coding_agent.py \
  --repo . \
  --patch /absolute/path/to/proposed-change.patch \
  --base-ref HEAD \
  --output artifacts/mkaos-coding-agent-report.json
```

A passing report means the proposed patch passed the configured checks in an isolated worktree; it does not prove correctness or security. Human review remains required. This initial stage consumes a proposed patch; it is not yet a model that independently diagnoses every failure, invents a reliable project-specific regression test, or automatically publishes a PR.

## Important boundaries

- Location services are provider-neutral contracts, not a live weather/traffic integration. A concrete provider, terms/license review, timeout/rate limits, and UI freshness display must be added before claiming live data is available.
- The security report tool is a local private report writer, not a vulnerability scanner. Keep original evidence restricted to authorized maintainers.
- GitHub accounts, billing, team permissions, and subscription enforcement are not implemented by a JSON policy file.
- No feature in this change can silently push or merge to `main`.

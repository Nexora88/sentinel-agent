# MKAOS supervised repair, location services, accounts and billing

## Implemented in this change

- `core/location_data_adapters.py`: consent-gated Open-Meteo weather and TomTom traffic adapters. Coordinates are validated; requests have bounded timeouts; responses are timestamped and carry `live`, `cached`, or `stale` freshness. The web API exposes `POST /api/location/weather` and `POST /api/location/traffic`. Weather needs no key for ordinary Open-Meteo usage; traffic requires `TOMTOM_API_KEY`. Review provider terms, quotas and local privacy requirements before deployment.
- `core/billing.py`: optional Stripe Checkout subscription creation, timestamped HMAC webhook verification, idempotent event handling and a local entitlement ledger. The API exposes `POST /api/billing/checkout`, `POST /api/billing/webhook`, and `GET /api/billing/status`. No card details are stored by MKAOS. Set Stripe keys, price ID and HTTPS return URLs in the deployment environment; no secrets belong in the repository. A valid signed Stripe event is required to update entitlements.
- `POST /api/accounts/register`: invite-only account creation using `MKAOS_TEAM_INVITE_TOKEN`; passwords must be at least 14 characters. Existing login and passkey paths remain in place. Local/free operation does not require creating a team account.
- `tools/mkaos_autonomous_repair_loop.py`: bounded failure-report → local coding CLI diagnosis → test-backed repair → compile/test gates → optional review PR. The agent command is an argv JSON array with explicit `{workspace}` and `{prompt_file}` placeholders, never a shell string. Credential-like environment variables are removed from the agent process. A Python regression test under `tests/` is required, attempts are capped at three, and PR publishing is opt-in with `--publish`. It never merges a PR.
- `core/local_voice.py`: local speech profiles are now named **Metehan** (male profile) and **Gökçe** (female profile). These are display names, not claims that the installed Piper model's original speaker identity or timbre changed.
- `config/mkaos-product-tiers.json`: local/free remains the default; team features cannot disable the baseline security policy.

## Configuration

Copy the new optional variables from `.env.example` into a private deployment environment. Keep `MKAOS_TEAM_INVITE_TOKEN`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and `TOMTOM_API_KEY` secret. The example file contains no live credentials.

For the repair loop, configure a local coding CLI as a JSON argv array, for example:

```json
["your-local-agent-cli", "--workspace", "{workspace}", "--prompt-file", "{prompt_file}"]
```

Then run from a clean local clone with a failure report that contains structured test/CI evidence:

```bash
python tools/mkaos_autonomous_repair_loop.py \
  --repo . \
  --failure-report /absolute/path/to/failure-report.json \
  --base-ref main \
  --agent-command-json '["your-local-agent-cli","--workspace","{workspace}","--prompt-file","{prompt_file}"]' \
  --max-attempts 2
```

Add `--publish` only when the local git remote and `gh` CLI are configured and you want the validated branch pushed and a review PR opened. No PR is merged automatically.

## Validation commands

```bash
python -m unittest discover -s tests -p 'test_location_data_adapters.py' -v
python -m unittest discover -s tests -p 'test_private_security_report.py' -v
python -m unittest discover -s tests -p 'test_mkaos_supervised_coding_agent.py' -v
python -m unittest discover -s tests -p 'test_mkaos_autonomous_repair_loop.py' -v
python -m unittest discover -s tests -p 'test_billing.py' -v
python -m unittest discover -s tests -p 'test_local_voice.py' -v
```

## Important boundaries

- Live provider adapters and API routes are implemented, but the actual service requires network access, user authorization, explicit per-request location consent, and provider availability. Freshness metadata is exposed by the API; the existing web UI still needs to display that status clearly to users.
- Stripe is implemented as an optional integration, not a configured merchant account. You must create the Stripe product/price, set HTTPS return URLs and webhook secret, configure the webhook endpoint, and test subscription lifecycle events in Stripe's test mode before charging real customers.
- Team registration is invitation-only and uses the existing local account store. This is not a hosted identity provider, email-verification workflow, password-reset service, or production multi-region identity database.
- The repair loop is an orchestration framework; it needs a compatible local coding CLI and structured failure report. It can make incorrect changes, so a test passing is not proof of correctness. Its worktree is process/workspace isolation, not a hardened OS sandbox. Use a disposable container for untrusted code, and retain human review as a mandatory gate.
- No code in this change automatically merges to `main`. The tools do not guarantee a diagnosis, a correct fix, or a PR for every failure.

# MKAOS tenant, offline and device validation

## Application enforcement

- Authenticated usernames select a canonical storage namespace under `memory/tenants/<username>/`.
- Each tenant receives separate RAG persistence, personal profile/vector memory, plans, research state, knowledge-pack output and media queue.
- Document uploads and deferred media inputs are saved under `memory/uploads/<username>/`.
- Generated images are stored within the tenant root; image retrieval requires authentication.
- Background job records carry an owner. Job lists and SSE events are filtered to the authenticated owner.
- Tenant identifiers pass the existing path-validation primitive before paths/cache keys are used.

## Migration and remaining review

Existing data in legacy shared `memory/` directories is **not automatically copied**. Back up legacy data and migrate only after independently establishing record ownership. This change scopes the principal RAG/personal memory/plans/research/uploads/application jobs, but does not prove every third-party agent cache, finance/permission artifact, or all legacy routes are fully tenant-migrated. Complete route-level cross-user tests and a deployment-specific review before public multi-tenant deployment.

## Offline evidence

Run `python scripts/validate_offline_egress.py` on Linux. It attempts a temporary network namespace with `unshare --net` and does not edit host firewall rules. PASS means the tested public IP/ports were unreachable only from that namespace. Failure to create the namespace is NOT PASS.

Host-level evidence requires a disposable test machine/VM, default-deny egress firewall, packet capture (for example `tcpdump -i any -nn`), timestamps and retained logs while exercising chat/RAG/file workflows with Wi-Fi disabled where relevant. Do not claim AIR-GAPPED from a UI toggle or this namespace test alone.

## Hardware gates

Run `python scripts/device_validation.py` on each target and retain the JSON output. Then perform a real local-model inference and preserve runtime logs proving which device executed it. CLI presence and GPU detection do not prove GPU inference.

Android app installation and Android on-device model inference are separate gates. Record device/Android version, app build/hash, model/license/provenance, successful prompt/response and proof inference stayed on-device with network disabled. ADB presence or app launch is not model-execution evidence.

For every model, complete `docs/model-provenance.template.json` from upstream license/source documents. Run the Turkish task fixture against the exact model and retain scored outputs for factuality, instruction following, Turkish fluency, safety and offline behavior. Fixtures alone are not a quality pass.

| Gate | CI evidence | External evidence still needed |
|---|---|---|
| Tenant/job isolation | Unit tests and per-tenant paths | Full cross-user API and legacy migration review |
| Offline | Validator contract tests | Host firewall + packet capture + Wi-Fi-off device run |
| NVIDIA/AMD/Apple | Portable diagnostics | Real inference logs on each GPU |
| Android | Desktop CI cannot prove it | Real device + local inference with network disabled |

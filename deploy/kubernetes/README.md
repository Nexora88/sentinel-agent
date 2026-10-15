# Kubernetes deployment scaffold

This is a restricted single-replica deployment scaffold, not a certified production chart.
Review every file before applying it.

## Required operator steps

1. Publish a reviewed image and replace the placeholder with an immutable image digest.
2. Create namespace mkaos-ingress and a trusted ingress controller labeled
   app.kubernetes.io/name=trusted-ingress; terminate TLS with a maintained controller.
3. Create secret sentinel-agent-secrets in namespace mkaos with keys owner-password
   and memory-key. The memory key must be random 32-byte data encoded as Base64.
   Do not commit Secret manifests or put keys in Git.
4. Copy public-config.example.yaml to a reviewed deployment config and set the exact
   production WebAuthn RP hostname and HTTPS origin.
5. Configure a StorageClass backed by encrypted storage, plus backup/restore tests,
   restricted secret access, and key rotation/recovery procedures.
6. Deploy an Ollama workload labeled app.kubernetes.io/name=ollama in this namespace
   and load only models whose licenses and provenance have been reviewed.
7. Validate that your CNI enforces NetworkPolicy. NetworkPolicy is not a substitute for
   mutual TLS; use a supported service mesh or mTLS-capable proxy between nodes if traffic
   crosses an untrusted network.
8. Validate HTTPS forwarding headers and WebAuthn on the actual browser/domain before
   exposing ingress.

## Review before applying

The image must support non-root UID 10001 and a read-only root filesystem. If it does
not, build and test a compatible image rather than weakening the pod security context
blindly. The NetworkPolicy assumes the DNS namespace and Ollama pod labels shown above.
Adjust them only after threat-model review. Egress intentionally denies general internet
access, so external research and external APIs will not work in this profile.

## Multi-replica scaling

Do not increase replicas until sessions, WebAuthn challenges, task idempotency, approval
records, and encrypted storage have a supported shared-store design. The current local
in-memory session/challenge state and ReadWriteOnce PVC are not a multi-replica data plane.
core.agent_mesh signs bounded task envelopes but does not provide P2P transport, encryption,
peer discovery, consensus, or remote execution.

# Private MKAOS agent mesh — WireGuard rollout

This repository intentionally contains no private keys, peer addresses, or live network
configuration. Provisioning is an operator-controlled deployment step; this repository
does not enable a tunnel or open firewall ports.

## Safe order

1. Assign a dedicated private mesh subnet (example only: \`10.77.0.0/24\`) and one \`/32\`
   address per agent. Do not reuse a LAN, VPN, or cloud subnet.
2. Generate each peer key locally with \`wg genkey\` and \`wg pubkey\`; store private keys
   in the host secret manager with mode \`0600\`. Never commit keys or paste them into chat.
3. Use one peer stanza per agent with a single peer \`/32\` in \`AllowedIPs\`. Do not use
   \`0.0.0.0/0\` or \`::/0\`; do not route general internet traffic through this mesh.
4. Firewall the WireGuard UDP port to known management sources. On the tunnel interface,
   allow only the minimum agent-to-agent ports and peer \`/32\` source/destination pairs;
   default-deny forwarding and unrelated inbound traffic.
5. Start with one non-production pair, validate route tables and firewall counters, then
   rotate keys and verify that the old public key no longer authenticates.
6. Run the app-level TLS 1.3 mutual-authentication layer over the tunnel. Require a CA
   trusted by both ends, URI SAN \`spiffe://mkaos/agent/<agent-id>\`, a local agent-ID
   allowlist, SHA-256 fingerprint revocation, and signed task-envelope replay protection.
7. Keep a tested rollback config and out-of-band console access before changing routes.

## Important limitations

- WireGuard encrypts the network tunnel; it does not by itself provide application-level
  identity, message authorization, or post-quantum security.
- \`core/mesh_tls.py\` provides context builders and post-handshake certificate identity
  checks only. There is no listener, certificate authority, automatic enrollment, live
  peer, or key revocation distribution service in this change.
- The existing \`core/agent_mesh.py\` Ed25519 envelope signature remains an additional
  integrity/replay layer; it is not a replacement for TLS confidentiality.
- Post-quantum or hybrid signatures/key exchange stay disabled until pinned implementations,
  wire-format interoperability, downgrade resistance, key rotation, and cross-version tests
  pass on the supported platforms.

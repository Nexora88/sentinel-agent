# Security Policy

## Supported versions

Security fixes are prioritized for the latest supported version on the default branch. Formal release support windows will be documented when established.

## Reporting a vulnerability

Do not publish exploit details, credentials, private data, or weaponized proof-of-concept code in a public issue. Use GitHub private vulnerability reporting for this repository when available. If it is not enabled, contact the repository maintainers privately through a verified GitHub account and request a secure reporting channel.

Include the affected commit/version, deployment profile, impact, minimal reproduction steps, and possible mitigation. Redact tokens, customer data and secrets. Test only systems you own or have explicit written authorization to assess.

## Scope and response

Reports concerning authentication, tenant isolation, data exposure, encryption/key handling, approval bypass, unsafe tool execution, dependencies and network-egress policy are in scope. Do not access other users' data, persist access, disrupt services, or perform unauthorized exploitation.

Maintainers should acknowledge reports, reproduce in an isolated environment, assess severity, coordinate a fix, add regression tests and publish a concise advisory after remediation. Response times depend on maintainer availability; no formal SLA is claimed.

## Security claims

Passing CI is not a security certification. ISO 27001, SOC 2 and Common Criteria require separate organizational controls and independent assessment. Hardware isolation, firewall behavior, TLS termination, key custody and backup recovery must be validated in the actual deployment.

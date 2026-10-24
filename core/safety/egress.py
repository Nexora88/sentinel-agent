"""Fail-closed application-layer egress URL policy.

This is a request-construction guard, NOT an OS firewall. It does not constrain
subprocesses, raw sockets, DNS packets, UDP, or other runtimes. Production
deployments must enforce a separate host/container network policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class EgressDecision:
    allowed: bool
    reason: str


class EgressPolicy:
    """Allow HTTPS requests only to explicitly configured exact hostnames.

    An empty allowlist denies all destinations. Subdomains are not implicitly
    trusted. Redirects must be disabled by the caller and each redirect target
    re-authorized independently.
    """

    def __init__(self, allowed_hosts: set[str] | frozenset[str] = frozenset()) -> None:
        normalized: set[str] = set()
        for host in allowed_hosts:
            value = host.strip().rstrip(".").lower()
            if not value or "/" in value or ":" in value or value.startswith("."):
                raise ValueError(f"Invalid exact hostname in egress allowlist: {host!r}")
            normalized.add(value)
        self._allowed_hosts = frozenset(normalized)

    @property
    def allowed_hosts(self) -> frozenset[str]:
        return self._allowed_hosts

    def authorize_url(self, url: str) -> EgressDecision:
        try:
            parsed = urlsplit(url)
            hostname = (parsed.hostname or "").rstrip(".").lower()
            port = parsed.port
        except (ValueError, TypeError):
            return EgressDecision(False, "Malformed URL")

        if parsed.scheme.lower() != "https":
            return EgressDecision(False, "Only HTTPS is permitted")
        if not hostname:
            return EgressDecision(False, "Missing hostname")
        if parsed.username is not None or parsed.password is not None:
            return EgressDecision(False, "Embedded URL credentials are forbidden")
        if port not in (None, 443):
            return EgressDecision(False, "Only HTTPS port 443 is permitted")
        if hostname not in self._allowed_hosts:
            return EgressDecision(False, "Destination is not explicitly allowlisted")
        return EgressDecision(True, "Allowed by exact-host HTTPS policy")


def require_authorized_url(url: str, policy: EgressPolicy) -> None:
    """Raise PermissionError unless the URL passes the fail-closed policy."""
    decision = policy.authorize_url(url)
    if not decision.allowed:
        raise PermissionError(f"MKAOS egress denied: {decision.reason}")

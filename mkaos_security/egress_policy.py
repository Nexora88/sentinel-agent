"""Fail-closed application-layer egress destination policy.

This validates destinations before an application initiates HTTP(S) requests. It is
NOT an OS firewall and cannot constrain subprocesses, raw sockets, UDP, or DNS outside
the caller. Enforce those paths with OS/container/network policy in deployment.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class EgressPolicy:
    """Allow only exact hostnames and explicitly listed TCP ports."""

    allowed_hosts: frozenset[str]
    allowed_ports: frozenset[int] = frozenset({443})
    allow_http_loopback: bool = False

    def __post_init__(self) -> None:
        normalized = frozenset(host.strip().lower().rstrip(".") for host in self.allowed_hosts)
        if not normalized or any(not host or "/" in host or ":" in host for host in normalized):
            raise ValueError("allowed_hosts must contain exact DNS hostnames, not URLs/IP:port entries")
        if any(port < 1 or port > 65535 for port in self.allowed_ports):
            raise ValueError("allowed port out of range")
        object.__setattr__(self, "allowed_hosts", normalized)

    def permits(self, url: str) -> bool:
        """Return False for malformed, ambiguous, credentialed, or non-allowlisted URLs."""
        try:
            parsed = urlsplit(url)
            if parsed.scheme not in {"https", "http"} or not parsed.hostname:
                return False
            if parsed.username is not None or parsed.password is not None:
                return False
            if parsed.fragment:
                # Fragments are not sent over HTTP and are irrelevant to authorization.
                pass
            host = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
            port = parsed.port
        except (ValueError, UnicodeError):
            return False
        if parsed.scheme == "http":
            if not (self.allow_http_loopback and host in {"localhost", "127.0.0.1", "::1"}):
                return False
        effective_port = port if port is not None else (443 if parsed.scheme == "https" else 80)
        if effective_port not in self.allowed_ports:
            return False
        # Exact hostname match only: no wildcard or suffix matching.
        return host in self.allowed_hosts


def require_permitted_url(url: str, policy: EgressPolicy) -> str:
    """Raise PermissionError before the caller makes a network request."""
    if not policy.permits(url):
        raise PermissionError(f"Outbound destination denied by MKAOS egress policy: {url!r}")
    return url

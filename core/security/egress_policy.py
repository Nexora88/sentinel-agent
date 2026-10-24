"""Default-deny URL egress policy for MKAOS outbound HTTP clients.

This is an application-layer destination check, not an OS firewall. Hosts must
also enforce network policy to prevent DNS rebinding and non-HTTP egress.
"""
from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlsplit


class EgressDenied(ValueError):
    """Raised when an outbound URL does not satisfy the configured policy."""


def allowed_hosts_from_env(value: str | None = None) -> frozenset[str]:
    raw = os.getenv("MKAOS_EGRESS_ALLOWED_HOSTS", "") if value is None else value
    hosts = set()
    for item in raw.split(","):
        host = item.strip().rstrip(".").lower()
        if not host:
            continue
        if any(ch in host for ch in "/:@*?#") or host.startswith("."):
            raise ValueError(f"Invalid exact hostname in MKAOS egress allowlist: {item!r}")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError("IP literals are not permitted in the hostname allowlist")
        if len(host) > 253 or any(not label or len(label) > 63 for label in host.split(".")):
            raise ValueError(f"Invalid hostname in MKAOS egress allowlist: {item!r}")
        hosts.add(host)
    return frozenset(hosts)


def authorize_egress_url(url: str, *, allowed_hosts: frozenset[str] | None = None) -> str:
    """Return the normalized URL or raise EgressDenied; deny by default."""
    if not isinstance(url, str) or not url or any(ord(c) < 32 for c in url):
        raise EgressDenied("Outbound URL is empty or contains control characters")
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").rstrip(".").lower()
        port = parsed.port
    except ValueError as exc:
        raise EgressDenied("Malformed outbound URL") from exc
    if parsed.scheme.lower() != "https":
        raise EgressDenied("Only HTTPS egress is permitted")
    if not host or parsed.username is not None or parsed.password is not None:
        raise EgressDenied("Missing host or embedded credentials")
    if parsed.fragment:
        raise EgressDenied("URL fragments are not allowed")
    if port not in (None, 443):
        raise EgressDenied("Only HTTPS port 443 is permitted")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise EgressDenied("IP-literal destinations are denied")
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".localhost", ".local", ".internal", ".lan")):
        raise EgressDenied("Local and internal destinations are denied")
    allowed = allowed_hosts_from_env() if allowed_hosts is None else allowed_hosts
    if host not in allowed:
        raise EgressDenied(f"Destination is not allowlisted: {host or '<missing>'}")
    return url

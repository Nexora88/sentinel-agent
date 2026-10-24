"""Fail-closed outbound TCP policy for the MKAOS Python process.

Set MKAOS_EGRESS_ALLOWLIST to comma-separated host:port entries, e.g.
"api.example.org:443,127.0.0.1:11434". Empty means no public outbound access.
This is an application-layer guard, not a replacement for an OS firewall.
"""
from __future__ import annotations

import ipaddress
import os
import socket
import threading
from urllib.parse import urlsplit

_LOCK = threading.Lock()
_INSTALLED = False
_ORIGINAL_CONNECT = socket.socket.connect
_ORIGINAL_CONNECT_EX = socket.socket.connect_ex
_LOOPBACK_NAMES = {"localhost"}
_LOOPBACK_PORTS = set()


class EgressDenied(OSError):
    """Raised when an outbound socket violates the configured policy."""


def _allowlist() -> set[tuple[str, int]]:
    entries = os.getenv("MKAOS_EGRESS_ALLOWLIST", "").strip()
    parsed: set[tuple[str, int]] = set()
    if not entries:
        return parsed
    for entry in entries.split(","):
        item = entry.strip()
        if not item:
            continue
        # IPv6 literals must use [address]:port to avoid ambiguous splitting.
        if item.startswith("["):
            end = item.find("]")
            if end < 0 or item[end + 1:end + 2] != ":":
                raise ValueError(f"Invalid egress allowlist entry: {item!r}")
            host, raw_port = item[1:end], item[end + 2:]
        else:
            if item.count(":") != 1:
                raise ValueError(f"Use host:port (bracket IPv6 literals): {item!r}")
            host, raw_port = item.rsplit(":", 1)
        try:
            port = int(raw_port)
        except ValueError as exc:
            raise ValueError(f"Invalid egress port in {item!r}") from exc
        if not host or not 1 <= port <= 65535:
            raise ValueError(f"Invalid egress host/port: {item!r}")
        parsed.add((host.rstrip(".").lower(), port))
    return parsed


def _is_loopback(host: str) -> bool:
    if host.lower().rstrip(".") in _LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def _is_permitted(address: object) -> bool:
    if not isinstance(address, tuple) or len(address) < 2:
        return False
    host, port = str(address[0]), int(address[1])
    try:
        ip = ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        # socket.connect normally receives a resolved IP; reject unresolved names
        # rather than allowing the socket layer to resolve them implicitly.
        return False

    # Local model/auth services are allowed only on loopback, never arbitrary LAN.
    if ip.is_loopback:
        return True
    if not ip.is_global:
        return False

    for allowed_host, allowed_port in _allowlist():
        if port != allowed_port:
            continue
        try:
            permitted_ips = {
                ipaddress.ip_address(row[4][0].split("%", 1)[0])
                for row in socket.getaddrinfo(allowed_host, allowed_port, type=socket.SOCK_STREAM)
            }
        except (OSError, ValueError):
            continue
        # Require the actual socket destination to match a fresh public DNS result.
        if ip in permitted_ips and ip.is_global:
            return True
    return False


def check_destination(address: object) -> None:
    """Raise EgressDenied unless the concrete destination is permitted."""
    if not _is_permitted(address):
        target = repr(address)
        raise EgressDenied(f"MKAOS egress denied by default-deny policy: {target}")


def install_egress_guard() -> None:
    """Enforce policy for TCP connect/connect_ex calls in this process."""
    global _INSTALLED
    with _LOCK:
        if _INSTALLED:
            return

        def guarded_connect(sock: socket.socket, address: object):
            check_destination(address)
            return _ORIGINAL_CONNECT(sock, address)

        def guarded_connect_ex(sock: socket.socket, address: object):
            try:
                check_destination(address)
            except (EgressDenied, OSError):
                return getattr(__import__("errno"), "EACCES", 13)
            return _ORIGINAL_CONNECT_EX(sock, address)

        socket.socket.connect = guarded_connect
        socket.socket.connect_ex = guarded_connect_ex
        _INSTALLED = True


def policy_status() -> dict:
    """Return a safe, secret-free summary suitable for diagnostics."""
    return {
        "enabled": _INSTALLED,
        "default": "deny",
        "allowlist_entries": len(_allowlist()),
        "loopback_allowed": True,
        "scope": "Python socket TCP connect/connect_ex; OS firewall still required",
    }

"""Isolated screenshot-only browser worker for private test labs.

No click/evaluate/download/API tools are exposed. Every request is restricted
to an explicit hostname allowlist and private/loopback IP space. The Docker
network must also be internal and must not publish a host port.
"""
from __future__ import annotations

import argparse
import ipaddress
import os
import socket
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError, sync_playwright


def _allowed_hosts() -> set[str]:
    hosts = {h.strip().lower().rstrip(".") for h in os.getenv("MKAOS_BROWSER_ALLOWED_HOSTS", "browser-fixture").split(",") if h.strip()}
    if not hosts:
        raise ValueError("MKAOS_BROWSER_ALLOWED_HOSTS must list at least one exact hostname.")
    return hosts


def _validate_url(url: str, allowed: set[str]) -> str:
    if not isinstance(url, str) or len(url) > 2048:
        raise ValueError("URL is missing or too long.")
    parts = urlsplit(url)
    host = (parts.hostname or "").lower().rstrip(".")
    if parts.scheme not in {"http", "https"} or not host or host not in allowed:
        raise ValueError("Only HTTP(S) URLs on the exact test-host allowlist are permitted.")
    if parts.username or parts.password or parts.fragment:
        raise ValueError("Credentials and URL fragments are not permitted.")
    try:
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except ValueError as exc:
        raise ValueError("Invalid URL port.") from exc
    try:
        addresses = {ipaddress.ip_address(item[4][0].split("%", 1)[0]) for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise ValueError("Allowlisted test hostname did not resolve.") from exc
    if not addresses or any(not (ip.is_private or ip.is_loopback or ip.is_link_local) for ip in addresses):
        raise ValueError("Browser worker refuses public or non-private target addresses.")
    return url


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Approved private test URL")
    parser.add_argument("--output", default="/screenshots/page.png", help="Screenshot path under /screenshots")
    parser.add_argument("--timeout-ms", type=int, default=15000)
    args = parser.parse_args()
    if not 1000 <= args.timeout_ms <= 30000:
        parser.error("--timeout-ms must be between 1000 and 30000.")
    allowed = _allowed_hosts()
    url = _validate_url(args.url, allowed)
    output = Path(args.output).resolve()
    if Path("/screenshots") not in output.parents:
        parser.error("--output must be a child of /screenshots.")
    output.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-background-networking", "--disable-component-update"])
        context = browser.new_context(accept_downloads=False, service_workers="block")
        page = context.new_page()
        def guard(route):
            try:
                _validate_url(route.request.url, allowed)
                route.continue_()
            except ValueError:
                route.abort("blockedbyclient")
        page.route("**/*", guard)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=args.timeout_ms)
            page.screenshot(path=str(output), full_page=True, animations="disabled")
            print(f"Screenshot saved: {output}")
        except (PlaywrightError, OSError) as exc:
            raise SystemExit(f"Browser task failed closed: {type(exc).__name__}") from exc
        finally:
            context.close()
            browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

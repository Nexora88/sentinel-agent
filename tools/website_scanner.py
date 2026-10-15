"""
Defensive Website Vulnerability Scanner.
Only scans public sites the operator is authorized to assess.
Private, loopback, link-local and metadata destinations are blocked to reduce SSRF risk.
No active exploitation is performed.
"""
from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Dict
from urllib.parse import urljoin, urlparse

import requests
from requests.exceptions import RequestException

logger = logging.getLogger("sentinel.website_scanner")
_REDIRECT_CODES = {301, 302, 303, 307, 308}


class UnsafeTarget(ValueError):
    pass


def validate_public_url(url: str) -> str:
    """Normalize URL and reject local/private targets before every request."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeTarget("Only http and https URLs are allowed.")
    if not parsed.hostname or parsed.username or parsed.password:
        raise UnsafeTarget("URL must include a hostname and must not contain credentials.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise UnsafeTarget("Invalid destination port.") from exc
    if port is not None and not (1 <= port <= 65535):
        raise UnsafeTarget("Invalid destination port.")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain", "metadata.google.internal"}:
        raise UnsafeTarget("Local and cloud metadata hosts are blocked.")
    try:
        literal = ipaddress.ip_address(host.strip("[]"))
        addresses = {literal}
    except ValueError:
        try:
            answers = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise UnsafeTarget("Hostname could not be resolved safely.") from exc
        addresses = {ipaddress.ip_address(answer[4][0].split("%")[0]) for answer in answers}
    if not addresses or any(
        not (ip.is_global and not ip.is_multicast and not ip.is_unspecified)
        for ip in addresses
    ):
        raise UnsafeTarget("Private, loopback, link-local or non-public destinations are blocked.")
    return url


class WebsiteScanner:
    """Basic defensive checks for public websites; redirects are validated manually."""

    def __init__(self, timeout: int = 10):
        self.timeout = max(1, min(int(timeout), 20))
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Sentinel-Agent-Defensive-Scanner/1.0"})
        self.session.trust_env = False

    def _get_public(self, url: str, timeout: int | None = None):
        current = validate_public_url(url)
        for _ in range(4):
            # Never let requests follow an unchecked redirect to an internal service.
            response = self.session.get(current, timeout=timeout or self.timeout, allow_redirects=False, stream=False)
            if response.status_code not in _REDIRECT_CODES:
                return response
            location = response.headers.get("Location")
            if not location:
                return response
            next_url = urljoin(current, location)
            response.close()
            validate_public_url(next_url)
            current = next_url
        raise UnsafeTarget("Too many redirects; scan stopped safely.")

    def scan(self, base_url: str) -> Dict:
        if not base_url.startswith(("http://", "https://")):
            base_url = "https://" + base_url
        results = {"url": base_url, "reachable": False, "issues": [], "info": {}}
        try:
            validate_public_url(base_url)
            resp = self._get_public(base_url)
            try:
                results["reachable"] = True
                results["status_code"] = resp.status_code
                results["final_url"] = resp.url
                headers = {k.lower(): v for k, v in resp.headers.items()}
                self._check_security_headers(headers, results)
                if not resp.url.startswith("https://"):
                    results["issues"].append({
                        "severity": "High", "title": "Site not served over HTTPS",
                        "description": "The site is accessible over plain HTTP.",
                        "recommendation": "Force HTTPS redirects and enable HSTS."
                    })
                if "server" in headers:
                    results["info"]["server"] = headers["server"]
                    results["issues"].append({
                        "severity": "Low", "title": "Server header disclosure",
                        "description": "The Server response header reveals implementation details.",
                        "recommendation": "Remove or minimize the Server header where practical."
                    })
                self._check_cookies(resp, results)
                self._check_sensitive_paths(resp.url, results)
            finally:
                resp.close()
        except UnsafeTarget as exc:
            results["issues"].append({
                "severity": "Info", "title": "Target blocked by safety policy",
                "description": str(exc),
                "recommendation": "Use a public hostname you own or are explicitly authorized to assess."
            })
        except RequestException as exc:
            logger.info("Website scan request failed: %s", type(exc).__name__)
            results["issues"].append({
                "severity": "Info", "title": "Could not reach the site",
                "description": "The request failed or timed out; response details were not exposed.",
                "recommendation": "Check the public URL and network connectivity."
            })
        return results

    def _check_security_headers(self, headers: Dict, results: Dict):
        recommended = {
            "strict-transport-security": "Missing HSTS header",
            "content-security-policy": "Missing Content-Security-Policy",
            "x-content-type-options": "Missing X-Content-Type-Options",
            "x-frame-options": "Missing X-Frame-Options",
            "referrer-policy": "Missing Referrer-Policy",
            "permissions-policy": "Missing Permissions-Policy",
        }
        for header, message in recommended.items():
            if header not in headers:
                severity = "Medium" if header in ("strict-transport-security", "content-security-policy") else "Low"
                results["issues"].append({
                    "severity": severity, "title": message,
                    "description": f"The response does not include the '{header}' header.",
                    "recommendation": f"Add a suitable {header} header."
                })

    def _check_cookies(self, resp, results: Dict):
        for cookie in resp.cookies:
            issues = []
            if not cookie.secure:
                issues.append("not Secure")
            if not cookie.has_nonstandard_attr("HttpOnly") and "HttpOnly" not in str(cookie):
                issues.append("not HttpOnly")
            if issues:
                results["issues"].append({
                    "severity": "Medium", "title": f"Insecure cookie: {cookie.name}",
                    "description": f"Cookie flags missing: {', '.join(issues)}",
                    "recommendation": "Set Secure and HttpOnly flags on sensitive cookies."
                })

    def _check_sensitive_paths(self, base_url: str, results: Dict):
        """Check a small fixed set of paths on the already validated public host."""
        paths = ["/.env", "/.git/config", "/backup.zip", "/phpinfo.php", "/admin",
                 "/wp-config.php.bak", "/server-status", "/debug", "/test"]
        for path in paths:
            try:
                url = urljoin(base_url, path)
                validate_public_url(url)
                response = self._get_public(url, timeout=5)
                try:
                    if response.status_code == 200 and len(response.content) > 50:
                        results["issues"].append({
                            "severity": "High", "title": f"Sensitive path accessible: {path}",
                            "description": f"The path {path} returned HTTP 200 with content.",
                            "recommendation": "Restrict access to this path (return 403/404)."
                        })
                finally:
                    response.close()
            except (RequestException, UnsafeTarget):
                continue

    def format_report(self, scan_result: Dict) -> str:
        lines = ["# Website Security Scan (Defensive)", f"URL: {scan_result.get('url')}",
                 f"Reachable: {scan_result.get('reachable')}",
                 f"Status: {scan_result.get('status_code', 'N/A')}", "", "## Issues Found"]
        issues = scan_result.get("issues", [])
        if not issues:
            lines.append("No obvious issues found with basic checks.")
        else:
            order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
            for issue in sorted(issues, key=lambda item: order.get(item.get("severity", "Info"), 4)):
                lines.extend([f"- **[{issue['severity']}] {issue['title']}**",
                              f"  {issue['description']}", f"  → {issue['recommendation']}", ""])
        return "\n".join(lines)

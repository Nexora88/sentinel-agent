"""
Defensive Website Vulnerability Scanner
Only scans sites you own / have permission for.
Never performs active exploitation.
"""

from __future__ import annotations

import logging
from typing import Dict, List
from urllib.parse import urljoin, urlparse

import requests
from requests.exceptions import RequestException

logger = logging.getLogger("sentinel.website_scanner")


class WebsiteScanner:
    """Basic defensive security checks for a website."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Sentinel-Agent-Defensive-Scanner/1.0"
        })

    def scan(self, base_url: str) -> Dict:
        """Run a set of defensive checks."""
        if not base_url.startswith(("http://", "https://")):
            base_url = "https://" + base_url

        results = {
            "url": base_url,
            "reachable": False,
            "issues": [],
            "info": {},
        }

        try:
            resp = self.session.get(base_url, timeout=self.timeout, allow_redirects=True)
            results["reachable"] = True
            results["status_code"] = resp.status_code
            results["final_url"] = resp.url

            # Security headers check
            headers = {k.lower(): v for k, v in resp.headers.items()}
            self._check_security_headers(headers, results)

            # HTTPS enforcement
            if not resp.url.startswith("https://"):
                results["issues"].append({
                    "severity": "High",
                    "title": "Site not served over HTTPS",
                    "description": "The site is accessible over plain HTTP. This exposes traffic to interception.",
                    "recommendation": "Force HTTPS redirects and enable HSTS."
                })

            # Server header disclosure
            if "server" in headers:
                results["info"]["server"] = headers["server"]
                results["issues"].append({
                    "severity": "Low",
                    "title": "Server header disclosure",
                    "description": f"Server header reveals: {headers['server']}",
                    "recommendation": "Remove or obfuscate the Server header."
                })

            # Basic cookie checks
            self._check_cookies(resp, results)

            # Common sensitive paths (only existence check, no exploitation)
            self._check_sensitive_paths(base_url, results)

        except RequestException as e:
            results["issues"].append({
                "severity": "Info",
                "title": "Could not reach the site",
                "description": str(e),
                "recommendation": "Check if the URL is correct and the site is online."
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
                    "severity": severity,
                    "title": message,
                    "description": f"The response does not include the '{header}' header.",
                    "recommendation": f"Add a proper {header} header."
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
                    "severity": "Medium",
                    "title": f"Insecure cookie: {cookie.name}",
                    "description": f"Cookie flags missing: {', '.join(issues)}",
                    "recommendation": "Set Secure and HttpOnly flags on sensitive cookies."
                })

    def _check_sensitive_paths(self, base_url: str, results: Dict):
        """Only checks if common sensitive paths return 200 (no exploitation)."""
        paths = [
            "/.env",
            "/.git/config",
            "/backup.zip",
            "/phpinfo.php",
            "/admin",
            "/wp-config.php.bak",
            "/server-status",
            "/debug",
            "/test",
        ]

        for path in paths:
            try:
                url = urljoin(base_url, path)
                r = self.session.get(url, timeout=5, allow_redirects=False)
                if r.status_code == 200 and len(r.content) > 50:
                    results["issues"].append({
                        "severity": "High",
                        "title": f"Sensitive path accessible: {path}",
                        "description": f"The path {path} returned HTTP 200 with content.",
                        "recommendation": "Block access to this path immediately (return 403/404)."
                    })
            except RequestException:
                continue

    def format_report(self, scan_result: Dict) -> str:
        """Turn scan result into readable text."""
        lines = [
            f"# Website Security Scan (Defensive)",
            f"URL: {scan_result.get('url')}",
            f"Reachable: {scan_result.get('reachable')}",
            f"Status: {scan_result.get('status_code', 'N/A')}",
            "",
            "## Issues Found",
        ]

        issues = scan_result.get("issues", [])
        if not issues:
            lines.append("No obvious issues found with basic checks.")
        else:
            for issue in sorted(issues, key=lambda x: ["Critical", "High", "Medium", "Low", "Info"].index(x["severity"])):
                lines.append(f"- **[{issue['severity']}] {issue['title']}**")
                lines.append(f"  {issue['description']}")
                lines.append(f"  → {issue['recommendation']}")
                lines.append("")

        return "\n".join(lines)

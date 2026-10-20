"""Write redacted security findings to a private local report, never to public issues."""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

SECRET_RE = re.compile(r"(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
SENSITIVE_KEYS = {"token", "secret", "password", "authorization", "private_key", "credential", "raw_evidence", "source_excerpt"}


def sanitize(value, key: str = ""):
    if key.lower() in SENSITIVE_KEYS:
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): sanitize(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value[:500]]
    if isinstance(value, str):
        return SECRET_RE.sub("[REDACTED_SECRET]", value[:2000])
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:500]


def write_private_report(findings: list[dict], output: Path) -> Path:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "visibility": "private-local-owner-review",
        "public_issue_created": False,
        "notice": "Findings are unverified evidence for authorized owner review, not proof of exploitability.",
        "findings": [sanitize(item) for item in findings[:500]],
    }
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        temporary.chmod(0o600)
    except OSError:
        pass
    os.replace(temporary, output)
    try:
        output.chmod(0o600)
    except OSError:
        pass
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="JSON file containing local findings")
    parser.add_argument("--output", default="artifacts/private-security-review.json")
    args = parser.parse_args()
    try:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        findings = payload.get("findings", payload) if isinstance(payload, dict) else payload
        if not isinstance(findings, list) or any(not isinstance(x, dict) for x in findings):
            raise ValueError("Expected a list of finding objects")
        print(write_private_report(findings, Path(args.output)))
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Private report not written: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

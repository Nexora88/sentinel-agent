#!/usr/bin/env python3
"""Tek tek doğrula: 12 Türkçe seed kaydı.

Her kayıt için kaydedilir:
  - source_uri
  - content_sha256 (prompt+newline+response baytlarından)
  - license_id + license_version
  - ai_training_allowed / weight_distribution_allowed / publish_allowed

Bu araç yasal görüş değildir; alanların dolu ve tutarlı olduğunu denetler.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ALLOWED_LICENSES = {"CC0-1.0", "CC-BY-4.0", "MIT", "Apache-2.0"}
REQUIRED = 12


def sha256_text(prompt: str, response: str) -> str:
    payload = (prompt.strip() + "\n" + response.strip()).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_records(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_no}: invalid JSON: {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"line {line_no}: record must be object")
        rows.append(obj)
    return rows


def verify(rows: list[dict]) -> tuple[list[dict], list[str]]:
    errors: list[str] = []
    verified: list[dict] = []
    if len(rows) != REQUIRED:
        errors.append(f"expected exactly {REQUIRED} records, found {len(rows)}")
    seen: set[str] = set()
    for index, row in enumerate(rows):
        sid = row.get("source_id")
        prefix = f"[{index}] {sid or 'no-id'}"
        for field in (
            "source_id",
            "source_uri",
            "license_id",
            "license_version",
            "prompt",
            "response",
        ):
            if not isinstance(row.get(field), str) or not str(row[field]).strip():
                errors.append(f"{prefix}: missing {field}")
        if isinstance(sid, str):
            if sid in seen:
                errors.append(f"{prefix}: duplicate source_id")
            seen.add(sid)
        uri = row.get("source_uri") or ""
        if not str(uri).startswith(("https://", "http://", "dataset://", "file://")):
            errors.append(f"{prefix}: source_uri must be auditable URI")
        lic = row.get("license_id")
        if lic not in ALLOWED_LICENSES:
            errors.append(f"{prefix}: license_id not allowlisted")
        for flag in ("ai_training_allowed", "weight_distribution_allowed", "publish_allowed"):
            if row.get(flag) is not True:
                errors.append(f"{prefix}: {flag} must be true for training seed")
        prompt = str(row.get("prompt", "")).strip()
        response = str(row.get("response", "")).strip()
        digest = sha256_text(prompt, response)
        declared = row.get("content_sha256")
        if declared and declared != digest:
            errors.append(f"{prefix}: content_sha256 mismatch (declared≠computed)")
        verified.append(
            {
                "source_id": sid,
                "source_uri": uri,
                "content_sha256": digest,
                "license_id": lic,
                "license_version": row.get("license_version"),
                "ai_training_allowed": True,
                "weight_distribution_allowed": True,
                "publish_allowed": True,
                "prompt": prompt,
                "response": response,
                "bytes": len((prompt + "\n" + response).encode("utf-8")),
            }
        )
    return verified, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("data/mkaos-tr-seed-12"),
        help="seed directory containing records.jsonl",
    )
    parser.add_argument(
        "--write-inventory",
        type=Path,
        default=None,
        help="write verified inventory JSON (never overwrites unless --force)",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    records_path = args.root / "records.jsonl"
    try:
        rows = load_records(records_path)
        verified, errors = verify(rows)
    except (OSError, ValueError) as exc:
        print(f"VERIFY_FAILED: {exc}", file=sys.stderr)
        return 2

    if errors:
        print("VERIFY_FAILED")
        for err in errors:
            print(err, file=sys.stderr)
        return 2

    print("VERIFY_OK")
    for item in verified:
        print(
            json.dumps(
                {
                    "source_id": item["source_id"],
                    "source_uri": item["source_uri"],
                    "content_sha256": item["content_sha256"],
                    "license_id": item["license_id"],
                    "license_version": item["license_version"],
                    "ai_training_allowed": item["ai_training_allowed"],
                    "weight_distribution_allowed": item["weight_distribution_allowed"],
                    "publish_allowed": item["publish_allowed"],
                    "bytes": item["bytes"],
                },
                ensure_ascii=False,
            )
        )

    if args.write_inventory:
        if args.write_inventory.exists() and not args.force:
            print(f"Refusing to overwrite {args.write_inventory}", file=sys.stderr)
            return 2
        args.write_inventory.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "mkaos-twelve-text-inventory-v1",
            "count": len(verified),
            "records": verified,
        }
        args.write_inventory.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        inv_hash = hashlib.sha256(args.write_inventory.read_bytes()).hexdigest()
        print(f"inventory_sha256={inv_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

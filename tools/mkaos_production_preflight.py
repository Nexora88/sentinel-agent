#!/usr/bin/env python3
"""Fail-closed MKAOS production readiness preflight.

This tool verifies configuration and local artifacts only. It never provisions
network interfaces, issues certificates, migrates user data, downloads model
weights, or starts services.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import ssl
import sys
from pathlib import Path


def check(label: str, ok: bool, detail: str) -> dict[str, str | bool]:
    return {"check": label, "ok": bool(ok), "detail": detail}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.add_argument("--model", type=Path, help="approved local model/checkpoint file")
    parser.add_argument("--model-sha256", help="expected SHA-256 for --model")
    parser.add_argument("--ca", type=Path, help="trusted CA PEM for mTLS deployment")
    parser.add_argument("--cert", type=Path, help="service certificate PEM")
    parser.add_argument("--key", type=Path, help="service private key PEM")
    parser.add_argument("--migration-source", type=Path, help="existing source data store")
    parser.add_argument("--migration-destination", type=Path, help="separate destination path")
    parser.add_argument("--require-network-config", action="store_true")
    args = parser.parse_args()

    results: list[dict[str, str | bool]] = []
    results.append(check("python", sys.version_info >= (3, 11), sys.version.split()[0]))
    results.append(check("openssl_tls13", ssl.HAS_TLSv1_3, "TLS 1.3 support available" if ssl.HAS_TLSv1_3 else "TLS 1.3 unavailable in this Python/OpenSSL build"))
    results.append(check("git", shutil.which("git") is not None, "git executable found" if shutil.which("git") else "git executable missing"))

    if args.require_network_config:
        required = ("MKAOS_PUBLIC_BASE_URL", "MKAOS_MTLS_CLIENT_CA", "MKAOS_ALLOWED_AGENT_IDS")
        for name in required:
            value = os.getenv(name, "").strip()
            ok = bool(value) and not re.search(r"(changeme|example\.com|your[_-]?key|placeholder)", value, re.I)
            results.append(check(f"env:{name}", ok, "configured" if ok else "missing or placeholder; configure through the deployment secret manager"))
        url = os.getenv("MKAOS_PUBLIC_BASE_URL", "").strip()
        results.append(check("https_public_url", url.startswith("https://"), "HTTPS URL configured" if url.startswith("https://") else "public URL must start with https://"))

    for label, path in (("mtls_ca", args.ca), ("mtls_certificate", args.cert), ("mtls_private_key", args.key)):
        if path is not None:
            exists = path.is_file()
            results.append(check(label, exists, f"file present: {path}" if exists else f"file missing: {path}"))
            if exists:
                try:
                    content = path.read_text(encoding="utf-8", errors="strict")
                    expected = "PRIVATE KEY" if label == "mtls_private_key" else "CERTIFICATE"
                    valid = "-----BEGIN " in content and expected in content
                    results.append(check(f"{label}_pem_shape", valid, "PEM marker found" if valid else "expected PEM marker not found"))
                except (OSError, UnicodeError) as exc:
                    results.append(check(f"{label}_readable", False, str(exc)))

    if args.model is not None:
        exists = args.model.is_file()
        results.append(check("model_file", exists, f"file present: {args.model}" if exists else f"model file missing: {args.model}"))
        if exists and args.model_sha256:
            actual = sha256_file(args.model)
            results.append(check("model_sha256", actual.lower() == args.model_sha256.lower(), f"actual SHA-256: {actual}"))
        elif exists:
            results.append(check("model_sha256", False, "expected hash is required; do not trust a filename alone"))

    if args.migration_source is not None or args.migration_destination is not None:
        src, dst = args.migration_source, args.migration_destination
        valid = bool(src and dst and src.exists() and src.resolve() != dst.resolve())
        results.append(check("migration_paths", valid, "source exists and destination is separate" if valid else "provide an existing source and a distinct destination; this preflight does not migrate data"))
        if src and dst and src.exists() and src.resolve() == dst.resolve():
            results.append(check("migration_safety", False, "source and destination must never be the same path"))

    passed = all(bool(item["ok"]) for item in results)
    report = {"ready": passed, "mode": "preflight-only", "checks": results,
              "notice": "Passing checks do not prove production security, mTLS handshake, model quality, or successful data migration."}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in results:
            print(f"[{'PASS' if item['ok'] else 'BLOCK'}] {item['check']}: {item['detail']}")
        print(f"\nReadiness preflight: {'PASS' if passed else 'BLOCKED'}")
        print(report["notice"])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Generate a local, evidence-oriented MKAOS provenance inventory.

This is a triage tool, not a license scanner or sovereignty certification.
It uses only the Python standard library and never fetches remote content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", "target",
    "dist", "build", ".pytest_cache", ".mypy_cache", "artifacts",
}
DEPENDENCY_NAMES = {
    "requirements.txt", "requirements-dev.txt", "pyproject.toml",
    "Pipfile", "Pipfile.lock", "poetry.lock", "uv.lock", "Cargo.toml",
    "Cargo.lock", "go.mod", "go.sum", "package.json", "package-lock.json",
    "pnpm-lock.yaml", "yarn.lock", "Dockerfile",
}
MODEL_SUFFIXES = {".safetensors", ".gguf", ".onnx", ".pt", ".pth", ".bin", ".model", ".tiktoken"}
MODEL_HINTS = ("tokenizer", "model_card", "dataset_card", "manifest", "sbom", "provenance")
REMOTE_MODEL_PATTERNS = (
    (re.compile(r"SmolLM2|smollm2", re.I), "third_party_model_reference"),
    (re.compile(r"huggingface\.co|hf_hub_download|from_pretrained", re.I), "model_hub_reference"),
    (re.compile(r"ollama", re.I), "ollama_reference"),
)
LICENSE_NAMES = {"LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "NOTICE", "THIRD_PARTY_NOTICES.md"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(root: Path):
    for current, dirs, files in __import__("os").walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(files):
            path = Path(current, name)
            try:
                if path.is_symlink() or not path.is_file():
                    continue
                yield path
            except OSError:
                continue


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strict", action="store_true",
                        help="exit non-zero if any unresolved provenance gates remain")
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"root is not a directory: {root}")

    inventory: list[dict[str, Any]] = []
    dependency_files: list[str] = []
    license_files: list[str] = []
    model_assets: list[dict[str, str]] = []
    references: list[dict[str, str]] = []

    for path in iter_files(root):
        rel = path.relative_to(root).as_posix()
        lower_name = path.name.lower()
        try:
            size = path.stat().st_size
            if path.name in DEPENDENCY_NAMES:
                dependency_files.append(rel)
            if path.name.upper() in LICENSE_NAMES:
                license_files.append(rel)
            if path.suffix.lower() in MODEL_SUFFIXES:
                model_assets.append({"path": rel, "sha256": sha256_file(path), "bytes": str(size)})
            if any(hint in lower_name for hint in MODEL_HINTS):
                inventory.append({"path": rel, "kind": "metadata_candidate",
                                  "sha256": sha256_file(path), "bytes": size,
                                  "review": "UNVERIFIED"})
            if path.name in DEPENDENCY_NAMES or path.suffix.lower() in MODEL_SUFFIXES:
                inventory.append({"path": rel,
                                  "kind": "dependency_manifest" if path.name in DEPENDENCY_NAMES else "model_asset",
                                  "sha256": sha256_file(path), "bytes": size,
                                  "review": "UNVERIFIED"})
            if path.suffix.lower() in {".py", ".rs", ".toml", ".yml", ".yaml", ".json", ".md", ".txt"} and size <= 2_000_000:
                try:
                    content = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                for pattern, kind in REMOTE_MODEL_PATTERNS:
                    if pattern.search(content):
                        references.append({"path": rel, "kind": kind, "review": "REVIEW_REQUIRED"})
        except OSError as exc:
            inventory.append({"path": rel, "kind": "read_error", "review": "UNVERIFIED",
                              "detail": type(exc).__name__})

    known_gaps = [
        "No approved real Turkish training corpus/checkpoint is certified by this static scan.",
        "The HTTP model path must be inspected separately; source references are not runtime proof.",
        "Transitive dependency licenses and origin require package-specific/SBOM review.",
        "Hardware, air-gap, Kubernetes, mTLS, revocation and multi-node claims require live tests.",
        "A file hash proves byte identity only, not authorship, origin, permission or safety.",
    ]
    report = {
        "schema_version": 1,
        "tool": "audit_mkaos_provenance.py",
        "root_name": root.name,
        "mode": "static_local_inventory_no_network",
        "status": "INCOMPLETE_REQUIRES_HUMAN_REVIEW",
        "summary": {
            "inventory_items": len(inventory),
            "dependency_manifest_count": len(dependency_files),
            "license_notice_file_count": len(license_files),
            "model_asset_count": len(model_assets),
            "model_or_runtime_reference_count": len(references),
            "unverified_inventory_items": sum(x.get("review") == "UNVERIFIED" for x in inventory),
        },
        "dependency_manifests": dependency_files,
        "license_notice_files": license_files,
        "model_assets": model_assets,
        "references_requiring_review": references,
        "inventory": inventory,
        "known_gaps": known_gaps,
        "limitations": [
            "Does not contact a network, verify URLs, interpret licenses or prove consent.",
            "Does not enumerate all transitive packages unless a complete lockfile is present.",
            "Does not attest to git authorship, hardware provenance, build reproducibility or runtime egress.",
            "A clean report must never be interpreted as a fully domestic/sovereign certification.",
        ],
    }
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    print(f"Report: {output}")
    if args.strict and (references or inventory or not dependency_files or not license_files):
        print("Strict mode: unresolved provenance evidence remains.", flush=True)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

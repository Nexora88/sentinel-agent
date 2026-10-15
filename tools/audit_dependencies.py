#!/usr/bin/env python3
"""Report dependency pinning and lockfile gaps without network access.

This is a local inventory, not a vulnerability database or legal opinion. Use
pip-audit/cargo-audit in a network-enabled review environment for advisories.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQ_RE = re.compile(r"^([A-Za-z0-9_.-]+)(?:\[[^]]+\])?\s*(.*)$")
EXACT_PYTHON = re.compile(r"^==\s*\d")
EXACT_CARGO = re.compile(r"^=\s*\d")


def python_requirements(path: Path) -> list[dict[str, str | bool]]:
    result = []
    if not path.exists():
        return result
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(("-", "git+", "http://", "https://")):
            if line.startswith(("-e ", "--editable ")):
                result.append({"file": str(path.relative_to(ROOT)), "requirement": line, "pinned": False})
            continue
        match = REQ_RE.match(line)
        if not match:
            result.append({"file": str(path.relative_to(ROOT)), "requirement": line, "pinned": False})
            continue
        spec = match.group(2).split(";")[0].strip()
        result.append({
            "file": str(path.relative_to(ROOT)),
            "requirement": line,
            "pinned": bool(EXACT_PYTHON.match(spec)),
        })
    return result


def cargo_dependencies(path: Path) -> list[dict[str, str | bool]]:
    if not path.exists():
        return []
    doc = tomllib.loads(path.read_text(encoding="utf-8"))
    result = []
    for group in ("dependencies", "dev-dependencies", "build-dependencies"):
        for name, value in doc.get(group, {}).items():
            if isinstance(value, str):
                spec, source = value, "registry"
            elif isinstance(value, dict):
                if "path" in value or "git" in value:
                    source = "path-or-git"
                    spec = str(value.get("rev") or value.get("tag") or value.get("branch") or value.get("path"))
                else:
                    source = "registry"
                    spec = str(value.get("version", ""))
            else:
                continue
            result.append({
                "file": str(path.relative_to(ROOT)),
                "requirement": f"{name} {spec}",
                "pinned": source != "registry" or bool(EXACT_CARGO.match(spec)),
            })
    return result


def build_report(root: Path = ROOT) -> dict:
    global ROOT
    ROOT = root.resolve()
    dependencies: list[dict[str, str | bool]] = []
    for name in ("requirements.txt", "requirements-voice.txt", "requirements-media.txt"):
        dependencies.extend(python_requirements(ROOT / name))
    for name in ("engine/mkaos-inference/Cargo.toml", "engine/mkaos-hf-adapter/Cargo.toml"):
        dependencies.extend(cargo_dependencies(ROOT / name))
    lockfiles = [
        str(p.relative_to(ROOT))
        for p in (ROOT / "requirements.lock", ROOT / "requirements-voice.lock",
                  ROOT / "requirements-media.lock", ROOT / "engine/mkaos-inference/Cargo.lock",
                  ROOT / "engine/mkaos-hf-adapter/Cargo.lock")
        if p.exists()
    ]
    unpinned = [item for item in dependencies if not item["pinned"]]
    return {
        "schema_version": 1,
        "network_accessed": False,
        "advisory_database_checked": False,
        "legal_review_performed": False,
        "dependency_count": len(dependencies),
        "pinned_count": len(dependencies) - len(unpinned),
        "unpinned_count": len(unpinned),
        "lockfiles_found": lockfiles,
        "lockfile_gaps": [name for name in (
            "requirements.lock", "requirements-voice.lock", "requirements-media.lock",
            "engine/mkaos-inference/Cargo.lock", "engine/mkaos-hf-adapter/Cargo.lock"
        ) if not (ROOT / name).exists()],
        "dependencies": dependencies,
        "unpinned": unpinned,
        "next_steps": [
            "Generate lockfiles from reviewed environments; do not guess package versions.",
            "Run pip-audit and cargo-audit against current advisory databases.",
            "Review licenses, transitive dependencies, source provenance and update diffs before merging.",
            "Re-run unit tests and offline/network-egress tests after dependency changes."
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true", help="exit nonzero if any dependency is not exactly pinned or lockfile is missing")
    args = parser.parse_args(argv)
    report = build_report(args.root)
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if args.strict and (report["unpinned_count"] or report["lockfile_gaps"]):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

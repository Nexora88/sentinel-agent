#!/usr/bin/env python3
"""Generate a local CycloneDX SBOM for the installed Python environment.

License metadata is evidence to review, not legal clearance. Missing license metadata
is reported explicitly; this tool never guesses a license or downloads package data.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirements_from(path: Path) -> set[str]:
    direct: set[str] = set()
    if not path.exists():
        return direct
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(("-", "http:", "https:")):
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)", line)
        if match:
            direct.add(normalize(match.group(1)))
    return direct


def license_metadata(dist: metadata.Distribution) -> list[dict[str, Any]]:
    expression = dist.metadata.get("License-Expression", "").strip()
    if expression:
        return [{"expression": expression}]
    classifiers = [
        item.removeprefix("License :: ").replace(" :: ", " / ")
        for item in dist.metadata.get_all("Classifier", [])
        if item.startswith("License :: ")
    ]
    if classifiers:
        return [{"license": {"name": item}} for item in sorted(set(classifiers))]
    legacy = dist.metadata.get("License", "").strip()
    if legacy and legacy not in {"UNKNOWN", "unknown"}:
        return [{"license": {"name": legacy[:500]}}]
    return []


def generate(output: Path, requirements: Path) -> dict[str, Any]:
    direct = requirements_from(requirements)
    components: list[dict[str, Any]] = []
    dependency_rows: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for dist in sorted(metadata.distributions(), key=lambda d: normalize(d.metadata.get("Name", ""))):
        name = dist.metadata.get("Name", "").strip()
        version = dist.version
        if not name or not version:
            continue
        normalized = normalize(name)
        purl = f"pkg:pypi/{normalized}@{version}"
        licenses = license_metadata(dist)
        if not licenses:
            unresolved.append(f"{name}=={version}")
        component: dict[str, Any] = {
            "type": "library",
            "bom-ref": purl,
            "name": name,
            "version": version,
            "purl": purl,
            "properties": [
                {"name": "mkaos:dependency-scope", "value": "direct" if normalized in direct else "transitive-or-tooling"},
                {"name": "mkaos:license-metadata", "value": "present" if licenses else "missing"},
            ],
        }
        if licenses:
            component["licenses"] = licenses
        components.append(component)
        dependencies: set[str] = set()
        for requirement in dist.metadata.get_all("Requires-Dist", []):
            match = re.match(r"\s*([A-Za-z0-9_.-]+)", requirement)
            if match:
                dependencies.add(normalize(match.group(1)))
        dependency_rows.append({"ref": purl, "dependsOn": sorted(
            f"pkg:pypi/{normalize(candidate.metadata.get('Name', ''))}@{candidate.version}"
            for candidate in metadata.distributions()
            if normalize(candidate.metadata.get("Name", "")) in dependencies
            and candidate.metadata.get("Name")
        )})

    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tools": [{"vendor": "Nexora88", "name": "MKAOS local SBOM generator", "version": "1.0.0"}],
            "properties": [
                {"name": "mkaos:license-review-status", "value": "INCOMPLETE_REQUIRES_HUMAN_REVIEW"},
                {"name": "mkaos:source", "value": str(requirements)},
            ],
        },
        "components": components,
        "dependencies": dependency_rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bom, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "output": str(output),
        "components": len(components),
        "direct_requirement_names": len(direct),
        "license_metadata_missing": len(unresolved),
        "unresolved_license_metadata": unresolved,
        "status": "INCOMPLETE_REQUIRES_HUMAN_REVIEW",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path, default=Path("requirements.txt"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/mkaos-sbom.cdx.json"))
    parser.add_argument("--strict-licenses", action="store_true", help="Exit nonzero if any installed package lacks license metadata")
    args = parser.parse_args()
    report = generate(args.output, args.requirements)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if args.strict_licenses and report["license_metadata_missing"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

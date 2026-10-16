#!/usr/bin/env python3
"""Create or verify a deterministic SHA-256 inventory of local MKAOS source files.

This records byte-level integrity only. It does not establish ownership, licence,
permission to train, or legal compliance. Keep source archives and generated
inventories out of Git unless their redistribution has been explicitly approved.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import sys
from pathlib import Path
from typing import Iterable

FIELDS = ("relative_path", "size_bytes", "sha256")
CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def inventory(root: Path, exclude: Path | None = None) -> list[tuple[str, int, str]]:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("--root must be a directory")
    excluded = exclude.resolve() if exclude is not None else None
    rows: list[tuple[str, int, str]] = []
    for candidate in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if candidate.is_symlink():
            raise ValueError(f"symlink refused (inventory must be explicit): {candidate}")
        if not candidate.is_file():
            continue
        resolved = candidate.resolve(strict=True)
        if excluded is not None and resolved == excluded:
            continue
        try:
            relative = resolved.relative_to(root).as_posix()
        except ValueError as exc:
            raise ValueError(f"path escapes root: {candidate}") from exc
        size, digest = sha256_file(resolved)
        rows.append((relative, size, digest))
    return rows


def render_tsv(rows: Iterable[tuple[str, int, str]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter="\t", lineterminator="\n")
    writer.writerow(FIELDS)
    for relative, size, digest in rows:
        writer.writerow((relative, size, digest))
    return output.getvalue()


def verify_tsv(root: Path, manifest: Path) -> tuple[bool, list[str]]:
    try:
        with manifest.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            if tuple(reader.fieldnames or ()) != FIELDS:
                return False, ["TSV header/schema mismatch"]
            expected = {}
            for row in reader:
                rel = row["relative_path"]
                if not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
                    return False, [f"unsafe path in manifest: {rel!r}"]
                if rel in expected:
                    return False, [f"duplicate path in manifest: {rel}"]
                expected[rel] = (row["size_bytes"], row["sha256"])
    except (OSError, UnicodeError, csv.Error) as exc:
        return False, [f"cannot read manifest: {exc}"]

    try:
        actual_rows = inventory(root, exclude=manifest)
    except (OSError, ValueError) as exc:
        return False, [str(exc)]
    actual = {rel: (str(size), digest) for rel, size, digest in actual_rows}
    issues: list[str] = []
    for rel in sorted(set(expected) - set(actual)):
        issues.append(f"missing from disk: {rel}")
    for rel in sorted(set(actual) - set(expected)):
        issues.append(f"not recorded in TSV: {rel}")
    for rel in sorted(set(expected) & set(actual)):
        if expected[rel] != actual[rel]:
            issues.append(f"size/hash mismatch: {rel}")
    return not issues, issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="directory containing local archives/TSV/source files")
    parser.add_argument("--output", type=Path, help="write a new inventory TSV; never overwrites an existing file")
    parser.add_argument("--verify", type=Path, help="verify an existing inventory TSV against current files")
    args = parser.parse_args(argv)
    if bool(args.output) == bool(args.verify):
        parser.error("choose exactly one of --output or --verify")
    try:
        if args.verify:
            ok, issues = verify_tsv(args.root, args.verify)
            print("VERIFY_OK" if ok else "VERIFY_FAILED")
            for issue in issues:
                print(issue, file=sys.stderr)
            if ok:
                size, digest = sha256_file(args.verify)
                print(f"inventory_tsv_bytes={size}")
                print(f"inventory_tsv_sha256={digest}")
            return 0 if ok else 2

        args.output.parent.mkdir(parents=True, exist_ok=True)
        rows = inventory(args.root, exclude=args.output)
        content = render_tsv(rows)
        with args.output.open("x", encoding="utf-8", newline="") as stream:
            stream.write(content)
        size, digest = sha256_file(args.output)
        print(f"files_hashed={len(rows)}")
        print(f"inventory_tsv={args.output}")
        print(f"inventory_tsv_bytes={size}")
        print(f"inventory_tsv_sha256={digest}")
        print("NOTE: hashes prove byte integrity only; they do not prove licence, consent, provenance, or legal permission.")
        return 0
    except FileExistsError:
        print(f"Refusing to overwrite: {args.output}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"Inventory failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

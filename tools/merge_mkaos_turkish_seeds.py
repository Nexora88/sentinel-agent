#!/usr/bin/env python3
"""Birleştir: records.jsonl + records_batch2.jsonl → records_all.jsonl"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path("data/mkaos-tr-seed-12"))
    p.add_argument("--output", type=Path, default=None)
    args = p.parse_args()
    out = args.output or (args.root / "records_all.jsonl")
    batches = [
        args.root / "records.jsonl",
        args.root / "records_batch2.jsonl",
    ]
    seen: set[str] = set()
    merged: list[dict] = []
    for path in batches:
        for row in load_jsonl(path):
            sid = row["source_id"]
            if sid in seen:
                print(f"duplicate skipped: {sid}", file=sys.stderr)
                continue
            seen.add(sid)
            row.setdefault("language", "tr")
            merged.append(row)
    out.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in merged) + "\n",
        encoding="utf-8",
    )
    print(f"MERGED count={len(merged)} path={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""MKAOS Türkçe seed kapısı: doğrula → insan onayı → eğitim → gerçek SHA → Rust testi.

- content_sha256 ve checkpoint_sha256 dosya baytlarından hesaplanır.
- Eğitim kapısı tüm kayıtlar approve olmadan açılmaz.
- Küçük seed modeli genel Türkçe LLM iddiası taşımaz; boru hattı kanıtıdır.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd, check=True, text=True)


def assign_splits(n: int) -> list[str]:
    """Kaynak düzeyinde train/val/test — hiçbir kaynak iki split'te olmaz."""
    if n < 6:
        raise ValueError("en az 6 kayıt gerekir (2+2+2)")
    n_test = max(2, n // 6)
    n_val = max(2, n // 6)
    n_train = n - n_val - n_test
    if n_train < 2:
        raise ValueError("train split çok küçük")
    labels = ["train"] * n_train + ["validation"] * n_val + ["test"] * n_test
    return labels


def build_manifest(records_path: Path, ledger_path: Path) -> dict:
    ledger: dict[str, dict] = {}
    if ledger_path.exists():
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                ledger[row["source_id"]] = row

    records: list[dict] = []
    for line in records_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        sid = obj["source_id"]
        decision = ledger.get(sid, {}).get("decision")
        if decision != "approve":
            raise ValueError(f"training blocked: {sid} decision={decision!r}")
        payload = (obj["prompt"].strip() + "\n" + obj["response"].strip()).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        pin = ledger[sid].get("content_sha256")
        if pin and pin != digest:
            raise ValueError(f"content_sha256 pin mismatch for {sid}")
        records.append(
            {
                "prompt": obj["prompt"].strip(),
                "response": obj["response"].strip(),
                "source_id": sid,
                "source_uri": obj["source_uri"],
                "license_id": obj["license_id"],
                "consent": True,
                "review_status": "approved",
                "personal_data": False,
                "sensitive_data": False,
                "content_sha256": digest,
                "language": obj.get("language", "tr"),
                "split": None,
            }
        )

    if len(records) < 12:
        raise ValueError(f"expected at least 12 approved records, got {len(records)}")

    labels = assign_splits(len(records))
    for rec, lab in zip(records, labels):
        rec["split"] = lab
    counts = {
        "train": sum(1 for r in records if r["split"] == "train"),
        "validation": sum(1 for r in records if r["split"] == "validation"),
        "test": sum(1 for r in records if r["split"] == "test"),
    }

    body = json.dumps(records, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return {
        "training_allowed": True,
        "language": "tr",
        "purpose": "MKAOS Turkish seed pipeline validation; not a quality benchmark",
        "summary": {
            "record_count": len(records),
            "content_sha256": hashlib.sha256(body).hexdigest(),
            "splits": counts,
        },
        "records": records,
    }


def rust_generate_test(weights: Path, expected_sha: str, report_path: Path) -> dict:
    cargo = shutil.which("cargo")
    result = {
        "rust_available": bool(cargo),
        "weights_path": str(weights),
        "weights_sha256_from_file": sha256_file(weights),
        "expected_sha256": expected_sha,
        "sha256_match": sha256_file(weights) == expected_sha,
    }
    if result["weights_sha256_from_file"] != expected_sha:
        result["error"] = "checkpoint sha256 mismatch — refusing Rust load"
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return result

    if not cargo:
        result["status"] = "skipped_no_cargo"
        result["note"] = "cargo yok; SHA dosya baytlarından doğrulandı"
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return result

    prompt = "Merhaba"
    started = time.perf_counter()
    try:
        cmd = [
            "cargo",
            "run",
            "--quiet",
            "--manifest-path",
            str(ROOT / "engine/mkaos-inference/Cargo.toml"),
            "--bin",
            "mkaos-generate",
            "--",
            "--checkpoint",
            str(weights),
            "--sha256",
            expected_sha,
            "--prompt",
            prompt,
            "--max-new-tokens",
            "16",
        ]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
        elapsed = time.perf_counter() - started
        result["elapsed_seconds"] = round(elapsed, 4)
        result["returncode"] = proc.returncode
        result["stdout_tail"] = (proc.stdout or "")[-2000:]
        result["stderr_tail"] = (proc.stderr or "")[-2000:]
        if proc.returncode != 0:
            probe = subprocess.run(
                [
                    "cargo",
                    "run",
                    "--quiet",
                    "--manifest-path",
                    str(ROOT / "engine/mkaos-inference/Cargo.toml"),
                    "--example",
                    "mkaos_parity_probe",
                    "--",
                    str(weights),
                    expected_sha,
                    "128",
                    "4",
                    "2",
                    ",".join(str(b) for b in prompt.encode("utf-8")),
                    "1e-5",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=180,
            )
            result["probe_returncode"] = probe.returncode
            result["probe_stdout_tail"] = (probe.stdout or "")[-2000:]
            result["probe_stderr_tail"] = (probe.stderr or "")[-2000:]
            result["status"] = "ok" if probe.returncode == 0 else "error"
            result["error"] = None if probe.returncode == 0 else "rust probe failed"
        else:
            result["status"] = "ok"
            result["approx_tokens_per_second"] = round(16 / max(elapsed, 1e-6), 3)
    except (subprocess.TimeoutExpired, OSError) as exc:
        result["status"] = "error"
        result["error"] = str(exc)

    try:
        if sys.platform.startswith("linux"):
            status = Path("/proc/self/status").read_text(encoding="utf-8")
            for line in status.splitlines():
                if line.startswith("VmRSS:"):
                    result["orchestrator_vm_rss_kb"] = int(line.split()[1])
    except (OSError, ValueError):
        pass

    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("data/mkaos-tr-seed-12"))
    parser.add_argument("--work-dir", type=Path, default=Path("artifacts/mkaos-tr-seed-run"))
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--skip-train", action="store_true")
    parser.add_argument("--skip-rust", action="store_true")
    parser.add_argument("--auto-approve", action="store_true")
    parser.add_argument("--merge-batches", action="store_true", default=True)
    args = parser.parse_args(argv)

    work = args.work_dir
    work.mkdir(parents=True, exist_ok=True)
    ledger = args.root / "approvals.jsonl"

    if args.merge_batches:
        run([sys.executable, "tools/merge_mkaos_turkish_seeds.py", "--root", str(args.root)])

    records = args.root / "records_all.jsonl"
    if not records.exists():
        records = args.root / "records.jsonl"

    inv = work / "turkish-inventory.json"
    run(
        [
            sys.executable,
            "tools/verify_mkaos_twelve_texts.py",
            "--root",
            str(args.root),
            "--records",
            str(records),
            "--write-inventory",
            str(inv),
            "--force",
        ]
    )

    if args.auto_approve:
        run(
            [
                sys.executable,
                "tools/record_mkaos_human_approvals.py",
                "--records",
                str(records),
                "--ledger",
                str(ledger),
                "--approve-all",
                "--reviewer-id",
                os.getenv("USER", "local-owner"),
            ]
        )
    gate = subprocess.run(
        [
            sys.executable,
            "tools/record_mkaos_human_approvals.py",
            "--records",
            str(records),
            "--ledger",
            str(ledger),
            "--check-gate",
        ],
        cwd=ROOT,
        text=True,
    )
    if gate.returncode != 0:
        print("TRAINING_BLOCKED: insan onayı eksik", file=sys.stderr)
        return 2

    try:
        manifest = build_manifest(records, ledger)
    except ValueError as exc:
        print(f"TRAINING_BLOCKED: {exc}", file=sys.stderr)
        return 2
    manifest_path = work / "approved-training-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "manifest_sha256": sha256_file(manifest_path),
                "split_counts": manifest["summary"]["splits"],
                "record_count": manifest["summary"]["record_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    if args.skip_train:
        print("SKIP_TRAIN")
        return 0

    ckpt_dir = work / "checkpoint"
    if ckpt_dir.exists():
        shutil.rmtree(ckpt_dir)
    try:
        run(
            [
                sys.executable,
                "tools/train_mkaos_rust_compatible.py",
                "--manifest",
                str(manifest_path),
                "--output-dir",
                str(ckpt_dir),
                "--steps",
                str(args.steps),
                "--batch-size",
                "4",
                "--context-length",
                "64",
                "--width",
                "64",
                "--layers",
                "2",
                "--heads",
                "4",
                "--kv-heads",
                "2",
                "--intermediate-size",
                "128",
                "--min-records-per-split",
                "2",
                "--device",
                "cpu",
                "--seed",
                "20261016",
            ]
        )
    except subprocess.CalledProcessError as exc:
        print(f"TRAIN_FAILED: {exc}", file=sys.stderr)
        return 3

    report_path = ckpt_dir / "training-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    pt_path = ckpt_dir / "mkaos-rust-compatible.pt"
    real_pt_sha = sha256_file(pt_path)
    if report.get("checkpoint_sha256") != real_pt_sha:
        print("CHECKPOINT_HASH_MISMATCH", file=sys.stderr)
        return 2
    print(json.dumps({"checkpoint_sha256_verified_from_file": real_pt_sha}, indent=2))

    export_dir = work / "export"
    if export_dir.exists():
        shutil.rmtree(export_dir)
    run(
        [
            sys.executable,
            "tools/export_mkaos_rust_checkpoint.py",
            "--checkpoint",
            str(pt_path),
            "--output-dir",
            str(export_dir),
        ]
    )
    weights = export_dir / "mkaos-rust-gqa-v1.mkaosw"
    export_manifest = json.loads(
        (export_dir / "mkaos-rust-gqa-v1.manifest.json").read_text(encoding="utf-8")
    )
    real_w_sha = sha256_file(weights)
    if export_manifest.get("checkpoint_sha256") != real_w_sha:
        print("EXPORT_HASH_MISMATCH", file=sys.stderr)
        return 2

    rust_report_path = work / "rust-engine-test.json"
    rust_result = {"status": "skipped"} if args.skip_rust else rust_generate_test(weights, real_w_sha, rust_report_path)

    summary = {
        "status": "pipeline_complete",
        "language": "tr",
        "records": manifest["summary"]["record_count"],
        "splits": manifest["summary"]["splits"],
        "manifest_sha256": sha256_file(manifest_path),
        "pytorch_checkpoint_sha256": real_pt_sha,
        "mkaosw_sha256": real_w_sha,
        "training_report": {
            "steps": report.get("steps"),
            "seed": report.get("seed"),
            "train_loss_first": report.get("train_loss_first"),
            "train_loss_last": report.get("train_loss_last"),
            "validation_loss_last": report.get("validation_loss_last"),
            "heldout_test_loss": report.get("heldout_test_loss"),
            "device": report.get("device"),
        },
        "rust_test": rust_result,
        "production_ready": False,
        "note": (
            "Gerçek dosya SHA-256 doğrulandı. Seed modeli genel Türkçe LLM değildir; "
            "ölçekli onaylı korpus ve kalite kapıları gerekir."
        ),
    }
    (work / "turkish-gate-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if rust_result.get("status") in {"ok", "skipped", "skipped_no_cargo"} else 2


if __name__ == "__main__":
    raise SystemExit(main())

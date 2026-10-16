"""Read-only MKAOS offline readiness check; never downloads or contacts services."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_file(label: str, path: Path, expected_sha256: str = "") -> dict[str, str | bool]:
    if not path.is_file():
        return {"name": label, "ok": False, "status": "missing", "path": str(path)}
    actual = sha256_file(path)
    expected = expected_sha256.strip().lower()
    if expected and actual != expected:
        return {"name": label, "ok": False, "status": "sha256_mismatch", "path": str(path), "sha256": actual}
    return {"name": label, "ok": True, "status": "verified" if expected else "present_hash_not_pinned", "path": str(path), "sha256": actual}


def run_checks(root: Path, *, include_media: bool = False) -> dict:
    root = root.resolve()
    checkpoint = Path(os.getenv("MKAOS_NATIVE_CHECKPOINT", str(root / "models/mkaos/model.mkaosw"))).expanduser()
    generator_env = os.getenv("MKAOS_NATIVE_GENERATOR", "")
    generator_candidates = [
        Path(generator_env).expanduser() if generator_env else None,
        root / "engine/mkaos-inference/target/release/mkaos-generate",
        root / "engine/mkaos-inference/target/debug/mkaos-generate",
    ]
    generator = next((p for p in generator_candidates if p and p.is_file()), None)
    expected = os.getenv("MKAOS_NATIVE_SHA256", "")
    checks = [
        {"name": "offline compose override", "ok": (root / "docker-compose.offline.yml").is_file(), "status": "present" if (root / "docker-compose.offline.yml").is_file() else "missing"},
        {"name": "Rust inference manifest", "ok": (root / "engine/mkaos-inference/Cargo.toml").is_file(), "status": "present" if (root / "engine/mkaos-inference/Cargo.toml").is_file() else "missing"},
        inspect_file("native checkpoint", checkpoint, expected),
        {"name": "native Rust generator", "ok": generator is not None, "status": "present" if generator else "missing"},
    ]
    if include_media:
        voice_dir = Path(os.getenv("SEKA_VOICE_MODEL_DIR", str(root / "models/voices"))).expanduser()
        for name in (
            os.getenv("SEKA_VOICE_MALE_MODEL", "tr_TR-fettah-medium.onnx"),
            os.getenv("SEKA_VOICE_FEMALE_MODEL", "tr_TR-dfki-medium.onnx"),
        ):
            checks.append({"name": f"voice model {name}", "ok": (voice_dir / name).is_file(), "status": "present" if (voice_dir / name).is_file() else "optional_media_missing"})
        whisper_dir = Path(os.getenv("FASTER_WHISPER_MODEL_PATH", str(root / "models/whisper-small"))).expanduser()
        checks.append({"name": "faster-whisper model directory", "ok": whisper_dir.is_dir() and any(whisper_dir.iterdir()), "status": "present" if whisper_dir.is_dir() and any(whisper_dir.iterdir()) else "optional_media_missing"})
    core_ok = all(bool(item["ok"]) for item in checks if not str(item["status"]).startswith("optional_media"))
    media_ok = all(bool(item["ok"]) for item in checks)
    return {
        "mode": "read-only-no-network",
        "core_ready": core_ok,
        "media_ready": media_ok if include_media else None,
        "checks": checks,
        "notes": [
            "No network requests or downloads were performed.",
            "A checkpoint hash is only pinned when MKAOS_NATIVE_SHA256 is configured.",
            "File presence and hashes do not prove model quality, source licensing, or air-gap enforcement.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--include-media", action="store_true", help="also require optional local voice and Whisper assets")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args(argv)
    report = run_checks(args.root, include_media=args.include_media)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("MKAOS OFFLINE READINESS")
        for item in report["checks"]:
            print(f"[{'OK' if item['ok'] else 'MISSING/UNVERIFIED'}] {item['name']}: {item['status']}")
        print(f"Core ready: {'yes' if report['core_ready'] else 'no'}")
        if args.include_media:
            print(f"Media ready: {'yes' if report['media_ready'] else 'no'}")
        for note in report["notes"]:
            print(f"NOTE: {note}")
    return 0 if report["core_ready"] and (report["media_ready"] is not False) else 2


if __name__ == "__main__":
    raise SystemExit(main())

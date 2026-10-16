from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_local_hash_recorder_hashes_actual_bytes_and_never_overwrites(tmp_path: Path) -> None:
    archive = tmp_path / "archive.tar.gz"
    tsv = tmp_path / "validated_sentences.tsv"
    output = tmp_path / "hashes.json"
    archive.write_bytes(b"archive bytes")
    tsv.write_bytes(b"sentence\tsource\nMerhaba\tfixture\n")

    command = [
        sys.executable, str(ROOT / "tools" / "record_mkaos_local_artifact_hashes.py"),
        "--archive", str(archive), "--tsv", str(tsv), "--output", str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["archive"]["sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert record["selected_tsv"]["sha256"] == hashlib.sha256(tsv.read_bytes()).hexdigest()
    assert record["raw_files_uploaded"] is False
    assert record["legal_or_training_approval"] is False

    again = subprocess.run(command, capture_output=True, text=True, check=False)
    assert again.returncode != 0
    assert "exists" in again.stderr


def test_local_hash_recorder_refuses_missing_files(tmp_path: Path) -> None:
    tsv = tmp_path / "data.tsv"
    tsv.write_text("sentence\tsource\nMerhaba\tfixture\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable, str(ROOT / "tools" / "record_mkaos_local_artifact_hashes.py"),
            "--archive", str(tmp_path / "missing.tar.gz"),
            "--tsv", str(tsv), "--output", str(tmp_path / "hashes.json"),
        ],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert not (tmp_path / "hashes.json").exists()

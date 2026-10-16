"""Canonical Python side of the MKAOS byte-tokenizer contract.
Rust parity is verified against data/mkaos/tokenizer-golden-vectors.tsv.
No normalization is performed: the exact UTF-8 byte sequence is tokenized.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "data" / "mkaos" / "tokenizer-contract.json"
CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
CONTRACT_ID = CONTRACT["contract_id"]
VOCAB_SIZE = int(CONTRACT["vocab_size"])
EOS_ID = int(CONTRACT["eos_id"])

if CONTRACT.get("encoding") != "UTF-8" or CONTRACT.get("normalization") != "none":
    raise RuntimeError("Unsupported MKAOS tokenizer contract; refuse implicit text normalization")
if VOCAB_SIZE != 257 or EOS_ID != 256:
    raise RuntimeError("This trainer supports only the MKAOS byte-v1 vocabulary")

def encode_text(text: str) -> list[int]:
    if not isinstance(text, str):
        raise TypeError("MKAOS tokenizer input must be str")
    return list(text.encode("utf-8"))

def decode_tokens(ids: list[int]) -> str:
    raw = bytearray()
    for token_id in ids:
        if token_id == EOS_ID:
            continue
        if not isinstance(token_id, int) or token_id < 0 or token_id > 255:
            raise ValueError(f"token id outside MKAOS byte-v1 vocabulary: {token_id!r}")
        raw.append(token_id)
    return raw.decode("utf-8", errors="replace")

def encode_documents(texts: list[str]) -> list[int]:
    ids: list[int] = []
    for text in texts:
        ids.extend(encode_text(text))
        ids.append(EOS_ID)
    return ids

def load_golden_vectors() -> list[tuple[str, str, list[int]]]:
    path = ROOT / "data" / "mkaos" / "tokenizer-golden-vectors.tsv"
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        parts = line.split("\\t")
        if len(parts) != 3:
            raise ValueError(f"{path}:{line_number}: expected name, text, token ids")
        name, text, encoded = parts
        ids = [int(value) for value in encoded.split(",")] if encoded else []
        rows.append((name, text, ids))
    if not rows:
        raise ValueError("MKAOS tokenizer golden vector set is empty")
    return rows

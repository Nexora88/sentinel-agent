"""Tenant-scoped storage path primitives.

This module is a security building block, not a claim that every legacy store
has been migrated. Callers must use the returned paths for all tenant data.
"""
from __future__ import annotations
import re
from pathlib import Path
_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")

def tenant_root(root: str | Path, user_id: str) -> Path:
    """Return a canonical per-user root; reject unsafe identities and escapes."""
    identity = str(user_id or "").strip().lower()
    if not _SAFE_ID.fullmatch(identity) or identity in {".", ".."}:
        raise ValueError("Geçersiz kullanıcı kimliği.")
    base = Path(root).expanduser().resolve()
    target = (base / identity).resolve()
    if target == base or base not in target.parents:
        raise ValueError("Kullanıcı depolama alanı kök dışına çıkamaz.")
    return target

def tenant_file(root: str | Path, user_id: str, filename: str) -> Path:
    """Resolve a simple filename within one user storage directory."""
    name = Path(str(filename or "")).name
    if not name or name in {".", ".."} or name != str(filename) or "\x00" in name:
        raise ValueError("Geçersiz dosya adı.")
    directory = tenant_root(root, user_id)
    target = (directory / name).resolve()
    if directory not in target.parents:
        raise ValueError("Dosya kullanıcı alanının dışına çıkamaz.")
    return target

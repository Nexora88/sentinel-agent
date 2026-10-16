"""Terminal komutları için sıkı beyaz liste.

LLM'den gelen her komut, çalıştırılmadan önce buradan geçmelidir.
Whitelist dışı = reddedilir. Bu bir güvenlik duvarı değildir; uygulama katmanı kontrolüdür.
"""
from __future__ import annotations

import re
import shlex
from typing import Tuple

# İlk token (program adı) izin listesi — genişletme bilinçli yapılır
ALLOWED_BINARIES = frozenset(
    {
        "python",
        "python3",
        "pip",
        "pip3",
        "pytest",
        "ruff",
        "mypy",
        "black",
        "git",
        "ls",
        "pwd",
        "cat",
        "head",
        "tail",
        "wc",
        "echo",
        "true",
        "false",
        "uname",
        "whoami",
        "date",
        "df",
        "du",
        "find",
        "grep",
        "rg",
        "sed",
        "awk",
        "sort",
        "uniq",
        "cargo",
        "rustc",
        "ffmpeg",
        "ffprobe",
        "ollama",
        "docker",
        "docker-compose",
        "npm",
        "node",
        "curl",  # sadece URL GET için; pipe engelli
    }
)

# Bu alt dizeler komutta asla olmamalı
HARD_DENY = [
    r"rm\s+-rf",
    r"rm\s+-r\s+/",
    r";\s*rm\b",
    r"&&\s*rm\b",
    r"\|\s*(ba)?sh\b",
    r"\|\s*sh\b",
    r"`",
    r"\$\(",
    r">\s*/dev/",
    r"mkfs",
    r"dd\s+if=",
    r"chmod\s+-R\s+777",
    r"curl\s+[^|]*\|\s*",
    r"wget\s+[^|]*\|\s*",
    r"base64\s+-d",
    r"/etc/passwd",
    r"/etc/shadow",
    r"\bnc\b.*-e",
    r"python\s+-c\s+['\"][^'\"]*os\.system",
    r"eval\s*\(",
    r"exec\s*\(",
]

GIT_ALLOWED_SUBCOMMANDS = frozenset(
    {
        "status",
        "diff",
        "log",
        "show",
        "branch",
        "rev-parse",
        "remote",
        "fetch",  # yazma değil; ağ iznine bağlı ayrı kapı
        "clone",  # dikkat: ağ
        "add",
        "commit",
        "checkout",
        "switch",
        "restore",
        "stash",
        "tag",
        "blame",
        "ls-files",
    }
)

# Push/reset --hard gibi tehlikeli git alt komutları burada yok; ayrı onay gerektirir
GIT_NEEDS_EXTRA_APPROVAL = frozenset({"push", "reset", "rebase", "clean", "filter-branch"})


def validate_command(cmd: str) -> Tuple[bool, str]:
    """Komut güvenli mi? (ok, neden)"""
    if not isinstance(cmd, str) or not cmd.strip():
        return False, "boş komut"
    if len(cmd) > 4000:
        return False, "komut çok uzun"
    if "\x00" in cmd:
        return False, "null bayt"

    for pat in HARD_DENY:
        if re.search(pat, cmd, re.IGNORECASE):
            return False, f"yasak desen: {pat}"

    # Çoklu komut / pipe zinciri: yalnızca tek basit komut
    if any(sep in cmd for sep in (";", "&&", "||", "\n", "\r")):
        return False, "çoklu komut veya zincir yasak"
    if "|" in cmd:
        return False, "pipe yasak (beyaz liste tek süreç)"

    try:
        parts = shlex.split(cmd)
    except ValueError as exc:
        return False, f"ayrıştırma hatası: {exc}"
    if not parts:
        return False, "boş"

    binary = parts[0].split("/")[-1]
    if binary not in ALLOWED_BINARIES:
        return False, f"program izin listesinde değil: {binary}"

    if binary == "git":
        if len(parts) < 2:
            return False, "git alt komut eksik"
        sub = parts[1]
        if sub in GIT_NEEDS_EXTRA_APPROVAL:
            return False, f"git {sub} ekstra insan onayı gerektirir"
        if sub not in GIT_ALLOWED_SUBCOMMANDS:
            return False, f"git alt komut izinli değil: {sub}"

    if binary in {"find", "grep", "rg"} and any(
        a.startswith("-") and "exec" in a for a in parts
    ):
        return False, "find/grep -exec yasak"

    return True, "ok"

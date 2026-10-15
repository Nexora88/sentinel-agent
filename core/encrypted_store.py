"""Small encrypted-at-rest file primitive for sensitive local state.

This does NOT encrypt Chroma/SQLite databases automatically. Callers must
explicitly route sensitive payloads through this class. The 256-bit key is
provided out-of-band as URL-safe/base64 MKAOS_MEMORY_KEY; it is never created
beside the data. Missing or malformed keys fail closed.
"""
from __future__ import annotations

import base64
import os
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_MAGIC = b"MKAOSENC\x01"
_KEY_ENV = "MKAOS_MEMORY_KEY"


class EncryptedStoreError(RuntimeError):
    """Raised when encrypted state cannot safely be read or written."""


def _decode_key(value: str | None = None) -> bytes:
    raw = value if value is not None else os.getenv(_KEY_ENV)
    if not raw:
        raise EncryptedStoreError(
            f"{_KEY_ENV} tanımlı değil; şifreli veri için anahtar gereklidir."
        )
    try:
        # Accept standard or URL-safe base64, with or without padding.
        padded = raw.strip() + "=" * (-len(raw.strip()) % 4)
        key = base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception as exc:
        raise EncryptedStoreError("Bellek anahtarı geçerli base64 biçiminde değil.") from exc
    if len(key) != 32:
        raise EncryptedStoreError("Bellek anahtarı tam 32 bayt (256 bit) olmalıdır.")
    return key


class EncryptedFileStore:
    """AES-256-GCM encrypted file with atomic replacement and authenticated header."""

    def __init__(self, path: str | Path, *, key: bytes | None = None):
        self.path = Path(path)
        self._key = key if key is not None else _decode_key()
        if len(self._key) != 32:
            raise EncryptedStoreError("AES-256-GCM anahtarı tam 32 bayt olmalıdır.")

    def write_bytes(self, plaintext: bytes) -> None:
        if not isinstance(plaintext, bytes):
            raise TypeError("Şifreli depoya yalnızca bytes yazılabilir.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        nonce = os.urandom(12)
        ciphertext = AESGCM(self._key).encrypt(nonce, plaintext, _MAGIC)
        payload = _MAGIC + nonce + ciphertext
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=str(self.path.parent), prefix=".encrypted-",
                suffix=".tmp", delete=False
            ) as tmp:
                temp_name = tmp.name
                tmp.write(payload)
                tmp.flush()
                os.fsync(tmp.fileno())
            try:
                os.chmod(temp_name, 0o600)
            except OSError:
                pass
            os.replace(temp_name, self.path)
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass
            # Persist the rename where the platform supports directory fsync.
            try:
                dir_fd = os.open(str(self.path.parent), os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except OSError:
                pass
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)

    def read_bytes(self) -> bytes:
        try:
            payload = self.path.read_bytes()
        except OSError as exc:
            raise EncryptedStoreError("Şifreli bellek dosyası okunamadı.") from exc
        if not payload.startswith(_MAGIC) or len(payload) < len(_MAGIC) + 12 + 16:
            raise EncryptedStoreError(
                "Dosya şifreli biçimde değil veya bozuk; düz metin olarak açılmayacak."
            )
        offset = len(_MAGIC)
        nonce = payload[offset:offset + 12]
        ciphertext = payload[offset + 12:]
        try:
            return AESGCM(self._key).decrypt(nonce, ciphertext, _MAGIC)
        except Exception as exc:
            raise EncryptedStoreError(
                "Bellek doğrulaması/şifresi başarısız; veri korunuyor, sıfırlanmıyor."
            ) from exc

    @classmethod
    def from_environment(cls, path: str | Path) -> "EncryptedFileStore":
        return cls(path, key=_decode_key())

"""Ed25519-signed human approval envelopes; never performs a push itself."""
from __future__ import annotations
import base64, hashlib, json, os, time
from pathlib import Path

class ApprovalProtocolError(ValueError): pass

class SignedApprovalProtocol:
    def __init__(self, audit_path: str = "./memory/approval_audit.jsonl", public_key_b64: str | None = None):
        self.audit_path = Path(audit_path)
        self.public_key_b64 = public_key_b64 if public_key_b64 is not None else os.getenv("MKAOS_APPROVAL_ED25519_PUBLIC_KEY", "")

    @staticmethod
    def canonical_payload(payload: dict) -> bytes:
        if not isinstance(payload, dict) or not payload.get("request_id") or not payload.get("action"):
            raise ApprovalProtocolError("İmzalı onayda request_id ve action zorunludur.")
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def verify(self, payload: dict, signature_b64: str, public_key_b64: str | None = None) -> dict:
        key_text = public_key_b64 or self.public_key_b64
        if not key_text: raise ApprovalProtocolError("Onay açık anahtarı ayarlanmamış.")
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            key = Ed25519PublicKey.from_public_bytes(base64.b64decode(key_text, validate=True))
            signature = base64.b64decode(signature_b64, validate=True)
            raw = self.canonical_payload(payload)
            key.verify(signature, raw)
        except ApprovalProtocolError: raise
        except Exception as exc: raise ApprovalProtocolError("İmza doğrulanamadı.") from exc
        digest = hashlib.sha256(self.canonical_payload(payload)).hexdigest()
        # Prevent replay of an already accepted request ID.
        if self.audit_path.exists():
            try:
                with self.audit_path.open("r", encoding="utf-8") as audit_file:
                    for line in audit_file:
                        previous = json.loads(line)
                    if previous.get("request_id") == str(payload["request_id"]) and previous.get("result") == "signature_validated":
                        raise ApprovalProtocolError("Bu onay isteği daha önce kullanılmış; replay engellendi.")
            except ApprovalProtocolError:
                raise
            except (OSError, ValueError):
                raise ApprovalProtocolError("Onay günlüğü okunamıyor; güvenlik için işlem durduruldu.")
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        record = {"timestamp": int(time.time()), "request_id": str(payload["request_id"]),
                  "action": str(payload["action"]), "payload_sha256": digest,
                  "signer_key_sha256": hashlib.sha256(base64.b64decode(key_text)).hexdigest(),
                  "result": "signature_validated", "note": "Bu kayıt tek başına GitHub push/merge çalıştırmaz."}
        fd = os.open(str(self.audit_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush(); os.fsync(handle.fileno())
        return {"valid": True, "record": record}

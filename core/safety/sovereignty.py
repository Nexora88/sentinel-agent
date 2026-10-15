"""Honest local-sovereignty status; no outbound probe is made here."""
from __future__ import annotations
import os
import socket
import stat
from pathlib import Path

CLOUD_MARKERS = (
    "K_SERVICE", "AWS_LAMBDA_FUNCTION_NAME", "VERCEL", "RAILWAY_ENVIRONMENT",
    "DYNO", "FLY_APP_NAME", "RENDER", "HEROKU_APP_NAME",
)

def sovereignty_status() -> dict:
    """Report evidence without pretending an environment variable proves isolation."""
    cloud_signals = [name for name in CLOUD_MARKERS if os.getenv(name)]
    hostname = socket.gethostname()
    configured_model = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    configured_media = os.getenv("SD_API_URL", "").strip()
    attestation_path = os.getenv("MKAOS_EGRESS_ATTESTATION_FILE", "").strip()
    attestation = {"present": False, "trusted_format": False, "details": "Ağ çıkışı denetlenmedi."}
    if attestation_path:
        try:
            path = Path(attestation_path)
            st = path.stat()
            secure_mode = not (stat.S_IMODE(st.st_mode) & 0o022)
            content = path.read_text(encoding="utf-8").strip()
            valid = secure_mode and content == "MKAOS-EGRESS-DENY-V1"
            attestation = {
                "present": True, "trusted_format": valid,
                "details": "Sunucu tarafından sağlanan kısıtlı izinli attestasyon mevcut." if valid
                else "Attestasyon dosyası eksik biçimde veya güvenli izinlerle doğrulanamadı.",
            }
        except OSError:
            attestation = {"present": False, "trusted_format": False, "details": "Attestasyon dosyası okunamadı."}
    if attestation["trusted_format"]:
        state = "host_attested"
        label = "HOST ATTESTED · ağ izolasyonu host kanıtına dayanıyor"
    elif cloud_signals:
        state = "cloud_detected"
        label = "BULUT ORTAMI TESPİT EDİLDİ · tam egemen değil"
    else:
        state = "local_or_unknown"
        label = "YEREL/ BİLİNMEYEN ORTAM · AIR-GAPPED doğrulanmadı"
    return {
        "state": state, "label": label, "fully_sovereign": False,
        "air_gapped_verified": False,
        "evidence": {
            "cloud_markers": cloud_signals, "hostname_available": bool(hostname),
            "model_endpoint_is_loopback": configured_model.startswith(("http://localhost", "http://127.0.0.1", "http://[::1]")),
            "self_hosted_media_configured": bool(configured_media),
            "host_attestation": attestation,
        },
        "limitations": [
            "Uygulama içi tespit işletim sistemi/firewall kurallarını tek başına kanıtlayamaz.",
            "HOST ATTESTED bir sunucu beyanıdır; bağımsız ağ denetiminin yerine geçmez.",
            "Model/medya uç noktaları ve GitHub entegrasyonu ayrıca ağ erişimi oluşturabilir.",
        ],
    }

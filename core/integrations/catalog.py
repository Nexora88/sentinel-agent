"""Integration readiness and permission policy; never claims reachability.
Secrets are checked for presence only and are never returned in status payloads.
"""
from __future__ import annotations
import os
from typing import Any

CATALOG: dict[str, dict[str, Any]] = {
    "github": {"name_tr": "GitHub", "network": True, "write_actions": ["create_issue", "create_branch", "commit", "open_pr", "merge_pr"], "env_any": [["GITHUB_TOKEN", "GH_TOKEN"]], "note_tr": "Yazma ve birleştirme işlemleri ayrıca onaylanmalıdır."},
    "canva": {"name_tr": "Canva", "network": True, "write_actions": ["create_design", "export_design"], "env_any": [["CANVA_ACCESS_TOKEN"]], "note_tr": "Canva erişim belirteci ve yetkili API kapsamları gerekir."},
    "mail": {"name_tr": "E-posta", "network": True, "write_actions": ["send_email"], "env_any": [["SMTP_HOST"], ["SMTP_USERNAME"], ["SMTP_PASSWORD"]], "note_tr": "E-posta dışarı veri aktarır; gönderim öncesi onay gerekir."},
    "google_finance": {"name_tr": "Google finans verileri", "network": True, "write_actions": [], "env_any": [["GOOGLE_FINANCE_API_KEY", "GOOGLE_API_KEY"]], "note_tr": "Anahtar varlığı, resmi Google Finance API erişimi bulunduğunu kanıtlamaz."},
    "tradingview": {"name_tr": "TradingView", "network": True, "write_actions": [], "env_any": [["TRADINGVIEW_API_BASE_URL"], ["TRADINGVIEW_API_TOKEN"]], "note_tr": "Yetkili erişim ve kullanım koşulları doğrulanmalı; izinsiz kazıma yapılmaz."},
    "weather": {"name_tr": "Hava durumu", "network": True, "write_actions": [], "env_any": [], "note_tr": "Ağsız modda canlı veri yoktur; önbellek ayrıca etiketlenmelidir."},
    "supabase": {"name_tr": "Supabase", "network": True, "write_actions": ["insert", "update", "delete", "upload"], "env_any": [["SUPABASE_URL"], ["SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"]], "note_tr": "RLS ve en az ayrıcalık uygulanmalı; service-role anahtarı istemciye verilmemelidir."},
    "vercel": {"name_tr": "Vercel", "network": True, "write_actions": ["deploy", "change_environment"], "env_any": [["VERCEL_TOKEN"]], "note_tr": "Dağıtım ve ortam değişiklikleri için açık onay gerekir."},
    "local_audio": {"name_tr": "Yerel ses çözümleme", "network": False, "write_actions": [], "env_any": [], "note_tr": "Yerel STT modeli ve çalışma zamanı ayrıca doğrulanmalıdır."},
    "local_image": {"name_tr": "Yerel görsel üretimi", "network": False, "write_actions": [], "env_any": [], "note_tr": "Yerel görsel modeli veya kendi yönettiğin model sunucusu gerekir."},
    "local_video": {"name_tr": "Yerel video oluşturma", "network": False, "write_actions": [], "env_any": [], "note_tr": "FFmpeg ve gerekli yerel medya araçları kurulmuş olmalıdır."},
}


def _groups_present(groups: list[list[str]]) -> bool:
    return all(any(os.getenv(name, "").strip() for name in group) for group in groups)


def integration_status(*, network_allowed: bool | None = None) -> dict[str, dict[str, Any]]:
    """Return safe metadata without exposing secrets or probing the network."""
    if network_allowed is None:
        network_allowed = os.getenv("MKAOS_NETWORK_MODE", "offline").strip().lower() not in {"offline", "airgap", "air-gapped", "disabled"}
    result: dict[str, dict[str, Any]] = {}
    for key, spec in CATALOG.items():
        configured = _groups_present(spec["env_any"])
        if spec["network"] and not network_allowed:
            state = "blocked_offline"
        elif spec["network"] and spec["env_any"] and not configured:
            state = "not_configured"
        elif spec["network"]:
            state = "configured_unverified" if spec["env_any"] else "network_required"
        else:
            state = "local_dependency_check_required"
        result[key] = {"name_tr": spec["name_tr"], "state": state, "network_required": spec["network"], "configured": configured, "write_actions": list(spec["write_actions"]), "note_tr": spec["note_tr"]}
    return result


def authorize_integration_action(integration: str, action: str, *, approved: bool = False, network_allowed: bool | None = None) -> dict[str, str]:
    """Fail closed for unknown actions, offline network, missing setup, and unapproved writes."""
    if integration not in CATALOG:
        raise ValueError("Bilinmeyen entegrasyon.")
    spec = CATALOG[integration]
    is_write = action in set(spec["write_actions"])
    if not is_write and not action.startswith("read:"):
        raise PermissionError("Eylem katalogda tanımlı değil; varsayılan olarak reddedildi.")
    if spec["network"]:
        if network_allowed is None:
            network_allowed = os.getenv("MKAOS_NETWORK_MODE", "offline").strip().lower() not in {"offline", "airgap", "air-gapped", "disabled"}
        if not network_allowed:
            raise PermissionError("Çevrimdışı modda ağ entegrasyonu engellendi.")
        if spec["env_any"] and not _groups_present(spec["env_any"]):
            raise PermissionError("Entegrasyon yapılandırılmamış; gerekli ayarları güvenli ortamda tamamla.")
    if is_write and not approved:
        raise PermissionError("Dış sistemde değişiklik için açık kullanıcı onayı gerekiyor.")
    return {"integration": integration, "action": action, "authorization": "approved_write" if is_write else "read_allowed"}

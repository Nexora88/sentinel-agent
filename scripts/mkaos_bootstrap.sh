#!/usr/bin/env bash
# MKAOS first-run setup. Model downloads are opt-in and require pinned SHA-256 entries.
set -Eeuo pipefail
umask 077

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"
ENV_FILE="$ROOT/.env"
ASSET_LOCK="$ROOT/config/model-assets.lock"

die() { printf 'HATA: %s\n' "$*" >&2; exit 1; }
info() { printf '[MKAOS] %s\n' "$*"; }

command -v python3 >/dev/null 2>&1 || die "Python 3 gerekli."
python3 - <<'PY' || die "Python 3.11 veya üzeri gerekli."
import sys
if sys.version_info < (3, 11):
    raise SystemExit(1)
PY
command -v docker >/dev/null 2>&1 || die "Docker kurulu değil. Docker Desktop veya Docker Engine kurup tekrar deneyin."
docker compose version >/dev/null 2>&1 || die "Docker Compose v2 gerekli."

if [[ ! -f "$ENV_FILE" ]]; then
  cp .env.example "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  info ".env oluşturuldu (izinler 600)."
fi

# Set a password only when OWNER_PASSWORD is blank. Never overwrite a supplied password.
BOOTSTRAP_PASSWORD="$(python3 - "$ENV_FILE" <<'PY'
from pathlib import Path
import secrets, string, sys
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
lines = text.splitlines()
found = False
password = ""
created = False
for i, line in enumerate(lines):
    if line.startswith("OWNER_PASSWORD="):
        found = True
        password = line.split("=", 1)[1].strip()
        if not password:
            created = True
            alphabet = string.ascii_letters + string.digits + "-_"
            password = "".join(secrets.choice(alphabet) for _ in range(32))
            lines[i] = "OWNER_PASSWORD=" + password
        break
if not found:
    created = True
    password = "".join(secrets.choice(string.ascii_letters + string.digits + "-_") for _ in range(32))
    lines.append("OWNER_PASSWORD=" + password)
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
path.chmod(0o600)
print(password if created else "")
PY
)"
if [[ -n "$BOOTSTRAP_PASSWORD" ]]; then
  info "Yeni OWNER_PASSWORD oluşturuldu; mevcut bir parola asla yeniden gösterilmez:"
  printf '\n  OWNER_PASSWORD=%s\n\n' "$BOOTSTRAP_PASSWORD"
  info "Parolayı parola yöneticisine kaydedin; terminal geçmişine veya ekran görüntülerine taşımayın."
fi
unset BOOTSTRAP_PASSWORD

TMP_DOWNLOAD=""
cleanup_download() { [[ -z "$TMP_DOWNLOAD" ]] || rm -f -- "$TMP_DOWNLOAD"; }
trap cleanup_download EXIT

download_assets() {
  [[ -f "$ASSET_LOCK" ]] || die "İndirilecek kilit dosyası yok: config/model-assets.lock. Önce her dosyanın güvenilir kaynağını ve SHA-256 değerini insan incelemesiyle doğrulayın."
  command -v curl >/dev/null 2>&1 || die "İsteğe bağlı model indirmesi için curl gerekli."
  command -v sha256sum >/dev/null 2>&1 || command -v shasum >/dev/null 2>&1 || die "SHA-256 aracı gerekli."

  local id url digest rel target actual
  while IFS=$'\t' read -r id url digest rel || [[ -n "${id:-}" ]]; do
    [[ -z "${id:-}" || "$id" == \#* ]] && continue
    [[ -n "${url:-}" && -n "${digest:-}" && -n "${rel:-}" ]] || die "Model kilit satırı eksik: id/url/sha256/path alanları gerekli."
    [[ "$url" == https://* ]] || die "$id için yalnızca HTTPS URL kabul edilir."
    [[ "$digest" =~ ^[a-fA-F0-9]{64}$ ]] || die "$id için geçerli 64 haneli SHA-256 gerekli."
    [[ "$rel" == models/* && "$rel" != *..* && "$rel" != /* ]] || die "$id yolu models/ altında güvenli bir göreli yol olmalı."
    target="$ROOT/$rel"
    mkdir -p -- "$(dirname -- "$target")"
    [[ ! -L "$target" ]] || die "Sembolik bağlantı hedefi reddedildi: $rel"
    if [[ -f "$target" ]]; then
      if command -v sha256sum >/dev/null 2>&1; then actual="$(sha256sum "$target" | cut -d ' ' -f1)"; else actual="$(shasum -a 256 "$target" | cut -d ' ' -f1)"; fi
      if [[ "${actual,,}" == "${digest,,}" ]]; then info "$id zaten doğrulanmış."; continue; fi
      die "$rel mevcut ancak SHA-256 uyuşmuyor. Dosyayı elle inceleyin; otomatik üzerine yazılmadı."
    fi
    TMP_DOWNLOAD="$(mktemp "${target}.download.XXXXXX")"
    info "$id indiriliyor (HTTPS + SHA-256 doğrulaması)..."
    curl --fail --silent --show-error --location --max-redirs 3 --proto '=https' --proto-redir '=https' "$url" -o "$TMP_DOWNLOAD"
    if command -v sha256sum >/dev/null 2>&1; then actual="$(sha256sum "$TMP_DOWNLOAD" | cut -d ' ' -f1)"; else actual="$(shasum -a 256 "$TMP_DOWNLOAD" | cut -d ' ' -f1)"; fi
    [[ "${actual,,}" == "${digest,,}" ]] || die "$id SHA-256 doğrulaması başarısız; indirilen geçici dosya silinecek."
    chmod 600 "$TMP_DOWNLOAD"
    mv -- "$TMP_DOWNLOAD" "$target"
    TMP_DOWNLOAD=""
    info "$id doğrulandı ve $rel konumuna yerleştirildi."
  done < "$ASSET_LOCK"
}

if [[ "${1:-}" == "--download-assets" ]]; then
  [[ -t 0 ]] || die "İzinli model indirmesi etkileşimli terminal gerektirir."
  printf 'Bu işlem model dosyalarını HTTPS üzerinden indirecek ve kilitli SHA-256 değerlerini doğrulayacak. Devam edilsin mi? [y/N] '
  read -r answer
  [[ "$answer" == "y" || "$answer" == "Y" ]] || die "Kullanıcı model indirmesini onaylamadı."
  download_assets
elif [[ -n "${1:-}" && "$1" != "--no-start" ]]; then
  die "Kullanım: scripts/mkaos_bootstrap.sh [--no-start | --download-assets]"
fi

info "Compose yapılandırması doğrulanıyor..."
docker compose config --quiet
if [[ "${1:-}" == "--no-start" ]]; then
  info "Kurulum ön kontrolü tamamlandı; servisler başlatılmadı."
  exit 0
fi
info "MKAOS imajı oluşturuluyor ve web servisi başlatılıyor..."
docker compose up --build -d sentinel
info "Başlangıç sağlık kontrolü..."
for attempt in $(seq 1 30); do
  if curl --fail --silent "http://127.0.0.1:${WEB_PORT:-8000}/health" >/dev/null 2>&1; then
    info "Web servisi sağlıklı: http://127.0.0.1:${WEB_PORT:-8000}"
    info "Eğitilmiş/onaylı checkpoint yoksa sohbetin HTTP 503 dönmesi beklenen davranıştır."
    exit 0
  fi
  sleep 2
done
docker compose logs --tail=80 sentinel >&2 || true
die "Web servisi 60 saniye içinde sağlıklı duruma geçmedi. Günlükleri inceleyin."

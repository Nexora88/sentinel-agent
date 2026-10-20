"""
MKAOS v6 — Mustafa Kemal Atatürk Operating System
Canlı işler · plan motoru · bilgi paketleri · Ollama
"""

from __future__ import annotations

import asyncio
import difflib
import json
import logging
import os
import queue
import re
import shutil
import tempfile
import uuid
import requests
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Request, Header, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

from core.pipeline import SentinelPipeline
from core.mkaos_native_chat import NativeMkaosUnavailable, generate_native_reply
from core.model_readiness import native_model_readiness
from core.tenant_storage import tenant_root, tenant_storage_id
from core.auth import AuthManager
from core.webauthn_auth import WebAuthnManager, WebAuthnError
from core.energy_policy import policy_status
from core.job_bus import job_bus
from core.local_voice import LocalVoiceError, voice_status, synthesize as synthesize_local_voice, transcribe as transcribe_local_voice
from core.night_scheduler import NightScheduler
from core.safety.sovereignty import sovereignty_status
from core.approval_protocol import SignedApprovalProtocol, ApprovalProtocolError
from core.improvement_gate import ImprovementProposalStore, ImprovementProposalError
from core.integrations.catalog import integration_status
from tools.clean_room_audit import scan_code_cleanliness

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seka.web")

app = FastAPI(title="MKAOS", version="6.5", description="Mustafa Kemal Atatürk Operating System — yerel ajan işletim sistemi")
webauthn = WebAuthnManager()

@app.middleware("http")
async def security_headers_and_https(request: Request, call_next):
    """Add browser hardening headers and optionally require HTTPS outside localhost."""
    is_local = request.url.hostname in {"localhost", "127.0.0.1", "::1"}
    scheme = request.url.scheme
    if os.getenv("TRUST_PROXY_HEADERS", "").strip().lower() in {"1", "true", "yes", "on"}:
        # Use only behind a trusted proxy that overwrites this header.
        forwarded = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip().lower()
        if forwarded in {"https", "http"}:
            scheme = forwarded
    require_https = os.getenv("REQUIRE_HTTPS", "true").strip().lower() in {"1", "true", "yes", "on"}
    if require_https and not is_local and scheme != "https":
        return Response("HTTPS is required for this deployment.", status_code=426)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(self), geolocation=()")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    if scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
UPLOAD_DIR = Path("./memory/uploads")
for d in (TEMPLATES_DIR, STATIC_DIR, UPLOAD_DIR):
    d.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

pipelines: dict[str, SentinelPipeline] = {}
night_scheduler: Optional[NightScheduler] = None
auth = AuthManager()
_encrypt_memory_files = os.getenv("MKAOS_ENCRYPT_MEMORY_FILES", "").strip().lower() in {"1", "true", "yes", "on"}
CHAT_HISTORY_FILE = Path("./memory/chat_history.enc" if _encrypt_memory_files else "./memory/chat_history.json")
LEGACY_CHAT_HISTORY_FILE = Path("./memory/chat_history.json")


def _load_chat_history() -> dict:
    if _encrypt_memory_files and LEGACY_CHAT_HISTORY_FILE.exists():
        raise RuntimeError("Plaintext chat history remains while encrypted memory is enabled; verify a protected backup and encrypted copy, then move or remove the plaintext file explicitly.")
    if not CHAT_HISTORY_FILE.exists():
        return {}
    try:
        if _encrypt_memory_files:
            from core.encrypted_store import EncryptedFileStore
            raw = EncryptedFileStore(CHAT_HISTORY_FILE).read_bytes()
            data = json.loads(raw.decode("utf-8"))
        else:
            data = json.loads(CHAT_HISTORY_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or any(not isinstance(v, list) for v in data.values()):
            raise ValueError("chat history must be a user-to-list mapping")
        return data
    except Exception as exc:
        raise RuntimeError(
            f"Chat history is unreadable; preserve and recover {CHAT_HISTORY_FILE} before restarting."
        ) from exc


def _save_chat_history() -> None:
    CHAT_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _encrypt_memory_files:
        from core.encrypted_store import EncryptedFileStore
        payload = json.dumps(chat_history, ensure_ascii=False, indent=2).encode("utf-8")
        EncryptedFileStore(CHAT_HISTORY_FILE).write_bytes(payload)
        return
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=str(CHAT_HISTORY_FILE.parent),
            prefix=".chat-history-", suffix=".tmp", delete=False
        ) as temp:
            json.dump(chat_history, temp, ensure_ascii=False, indent=2)
            temp.flush()
            os.fsync(temp.fileno())
            temp_name = temp.name
        try:
            os.chmod(temp_name, 0o600)
        except OSError:
            pass
        os.replace(temp_name, CHAT_HISTORY_FILE)
        try:
            os.chmod(CHAT_HISTORY_FILE, 0o600)
        except OSError:
            pass
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


chat_history = _load_chat_history()

MANIFESTO = {
    "name": "MKAOS",
    "version": "6.5",
    "tagline": "Mustafa Kemal Atatürk Operating System · İstikbal Siber Göklerdedir · yerel egemenlik",
    "pillars": [
        "Yerel model çekirdeği ve denetlenebilir ajan planları",
        "Ağ çıkışı engellendiğinde AIR-GAPPED; doğrulanmadıysa egemenlik iddiası yok",
        "İstikbal Siber Göklerdedir — bilgi, üretim ve bağımsızlık",
        "Bilgi evreni: sanitize + güven skoru ile büyür",
        "İzin modeli: yazma/push asla otomatik değil",
        "Paper finans: sanal para, kilitli risk kuralları",
        "Plan motoru: çok adımlı emir, onay kapıları",
        "Canlı iş kuyruğu (SSE)",
        "Paylaşılabilir bilgi paketi (kişisel veri yok)",
        "Türkçe komut köprüsü + paneller",
    ],
    "not_included": [
        "Otonom şirket / gerçek trading",
        "Açık P2P sürü / uzaktan kod çalıştırma",
        "IoT cihaz kontrolü",
    ],
}


def get_pipeline(tenant_id: str = "owner") -> SentinelPipeline:
    identity = str(tenant_id or "owner").strip().lower()
    tenant_root("./memory/tenants", tenant_storage_id(identity))
    if identity not in pipelines:
        pipelines[identity] = SentinelPipeline(tenant_id=identity)
    return pipelines[identity]


def get_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        if os.getenv("AUTH_REQUIRED", "true").lower() != "true":
            return {"username": "owner", "role": "owner", "display_name": "Sahip"}
        raise HTTPException(401, "Yetki gerekli")
    token = authorization.replace("Bearer ", "").strip()
    session = auth.validate(token)
    if not session:
        raise HTTPException(401, "Geçersiz oturum")
    return session


class ChatRequest(BaseModel):
    message: str

class ExpandRequest(BaseModel):
    topic: Optional[str] = None

class SeedRequest(BaseModel):
    topic: str

class LoginRequest(BaseModel):
    username: str
    password: str

class PasskeyOptionsRequest(BaseModel):
    username: str

class PasskeyVerifyRequest(BaseModel):
    challenge_id: str
    credential: dict

class ImageRequest(BaseModel):
    prompt: str
    width: int = 768
    height: int = 768

class FinanceRequest(BaseModel):
    query: str

class LegacyRequest(BaseModel):
    passphrase: str

class PlanRequest(BaseModel):
    goal: str

class PackRequest(BaseModel):
    title: Optional[str] = "MKAOS Araştırma Paketi"

class MediaQueueRequest(BaseModel):
    operation: str = "generate"
    prompt: str
    width: int = 768
    height: int = 768

class ForgetRequest(BaseModel):
    topic: str
    last_hours: int = 24
    confirmation: str

class ApprovalVerifyRequest(BaseModel):
    payload: dict
    signature_b64: str

class VoiceRequest(BaseModel):
    text: str
    voice: str = "male"
    cat_mode: bool = False
    pace: float = 1.0



def _run_night_with_infographic() -> dict:
    result = get_pipeline().run_night_research()
    summary = result.get("summary") if isinstance(result, dict) else str(result)
    visual = get_pipeline().media_engine.render_report_infographic(str(summary or result)[:4000])
    if isinstance(result, dict):
        result["infographic"] = visual
        if visual.get("success"):
            result["summary"] = (str(summary or "Gece denetimi tamamlandı.") + " · Yerel infografik: " + visual["filename"])[:800]
        return result
    return {"summary": str(result)[:800], "infographic": visual}


@app.on_event("startup")
async def startup():
    # Keep the web process available even if Ollama/models are temporarily offline.
    # Nightly maintenance writes reports/proposals only; it never edits or pushes code.
    global night_scheduler
    logger.info("MKAOS v6.5 — lazy local model initialization")
    enabled = os.getenv("SEKA_NIGHT_AUTORUN", "true").strip().lower() in {"1", "true", "yes", "on"}
    try:
        night_scheduler = NightScheduler(
            runner=lambda: _run_night_with_infographic(),
            enabled=enabled,
            hour=int(os.getenv("SEKA_NIGHT_HOUR", "3")),
            minute=int(os.getenv("SEKA_NIGHT_MINUTE", "0")),
            timezone_name=os.getenv("SEKA_TIMEZONE", "Europe/Istanbul"),
            state_path=os.getenv("SEKA_NIGHT_STATE_PATH", "./memory/night_scheduler.json"),
        )
        night_scheduler.start()
        logger.info("MKAOS nightly audit enabled=%s schedule=%s", enabled, night_scheduler.status()["scheduled_time"])
    except Exception as exc:
        # Scheduler configuration failure must not take down the web panel.
        logger.exception("Night scheduler unavailable (%s).", type(exc).__name__)
        night_scheduler = None


@app.on_event("shutdown")
async def shutdown():
    if night_scheduler:
        night_scheduler.stop()


@app.get("/health")
async def health():
    # Container health must not depend on the Ollama model being loaded.
    return {"status": "ok", "service": "MKAOS", "version": "6.4", "model_checked": False}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/model/readiness")
async def api_model_readiness():
    """Expose model readiness without leaking local paths or checkpoint digests."""
    return native_model_readiness()


@app.get("/api/manifesto")
async def api_manifesto():
    return MANIFESTO


@app.post("/api/login")
async def login(req: LoginRequest):
    token = auth.authenticate(req.username, req.password)
    if not token:
        raise HTTPException(401, "Hatalı kullanıcı veya şifre")
    return {"token": token, "user": auth.validate(token)}


@app.get("/api/webauthn/capabilities")
async def webauthn_capabilities():
    return webauthn.capabilities()

@app.post("/api/webauthn/register/options")
async def webauthn_register_options(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    try:
        return webauthn.registration_options(user["username"], user.get("display_name") or user["username"])
    except WebAuthnError as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post("/api/webauthn/register/verify")
async def webauthn_register_verify(req: PasskeyVerifyRequest, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    try:
        return webauthn.verify_registration_for_user(req.challenge_id, req.credential, user["username"])
    except WebAuthnError as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post("/api/webauthn/login/options")
async def webauthn_login_options(req: PasskeyOptionsRequest):
    username = req.username.lower().strip()
    account = auth._users.get(username)
    if not account or not account.get("active"):
        raise HTTPException(401, "Hesap veya kayıtlı passkey bulunamadı")
    try:
        return webauthn.authentication_options(username)
    except WebAuthnError as exc:
        raise HTTPException(401, "Hesap veya kayıtlı passkey bulunamadı") from exc

@app.post("/api/webauthn/login/verify")
async def webauthn_login_verify(req: PasskeyVerifyRequest):
    try:
        username = webauthn.verify_authentication(req.challenge_id, req.credential)
        token = auth.create_session_for_verified_user(username)
        if not token:
            raise HTTPException(401, "Hesap etkin değil")
        return {"token": token, "user": auth.validate(token)}
    except WebAuthnError as exc:
        raise HTTPException(401, "Passkey doğrulaması başarısız") from exc

@app.get("/api/voice/status")
async def api_voice_status(authorization: Optional[str] = Header(None)):
    get_user(authorization)
    return voice_status()


@app.post("/api/voice/synthesize")
async def api_voice_synthesize(req: VoiceRequest, authorization: Optional[str] = Header(None)):
    get_user(authorization)
    try:
        audio = synthesize_local_voice(req.text, req.voice, req.cat_mode, req.pace)
    except LocalVoiceError as exc:
        raise HTTPException(503, str(exc))
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@app.post("/api/voice/transcribe")
async def api_voice_transcribe(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    get_user(authorization)
    suffix = Path(file.filename or "speech.webm").suffix.lower()
    if suffix not in {".webm", ".wav", ".mp3", ".m4a", ".ogg"}:
        raise HTTPException(400, "Desteklenmeyen ses biçimi.")
    audio = await file.read(15 * 1024 * 1024 + 1)
    await file.close()
    try:
        transcript = transcribe_local_voice(audio, suffix)
    except LocalVoiceError as exc:
        raise HTTPException(503, str(exc))
    return {"text": transcript, "mode": "local-only"}




def _ollama_status(p: SentinelPipeline) -> dict:
    """Probe only the configured local Ollama endpoint with a short timeout."""
    base_url = str(getattr(p.ollama, "base_url", "http://localhost:11434")).rstrip("/")
    session = requests.Session()
    session.trust_env = False
    try:
        response = session.get(base_url + "/api/tags", timeout=(0.4, 1.0))
        response.raise_for_status()
        payload = response.json()
        names = {
            str(item.get("name", "")).split(":")[0]
            for item in payload.get("models", [])
            if isinstance(item, dict)
        }
        expected = str(getattr(p.ollama, "model_name", "")).split(":")[0]
        if expected and expected not in names:
            return {
                "status": "model_missing",
                "message": f"Ollama çalışıyor ancak {getattr(p.ollama, 'model_name', expected)} modeli yerelde bulunamadı.",
                "model": getattr(p.ollama, "model_name", ""),
                "base_url": base_url,
            }
        return {"status": "online", "message": "Yerel Ollama bağlantısı hazır.", "base_url": base_url}
    except Exception:
        return {
            "status": "unavailable",
            "message": "Ollama'ya bağlanılamadı. Hizmeti ve yerel bağlantı adresini kontrol et.",
            "base_url": base_url,
        }
    finally:
        session.close()


@app.get("/api/status")
async def api_status(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    try:
        p = get_pipeline(user["username"])
    except Exception as exc:
        logger.warning("MKAOS bileşenleri başlatılamadı (%s).", type(exc).__name__)
        return {
            "brand": "MKAOS", "version": "6.5", "status": "degraded", "user": user,
            "assistant": {"status": "degraded", "message": "MKAOS paneli açık; yerel bellek veya model bileşeni başlatılamadı. Veriler otomatik silinmedi."},
            "ollama": {"status": "unavailable", "message": "Ollama bağlantısı hazır değil. Ollama hizmetini, model kurulumunu ve yerel bellek dizinini kontrol et."},
            "privacy": {"web_research": False, "external_finance_data": False, "site_scanning": False, "external_notifications": False, "github_network_access": False},
            "night_scheduler": night_scheduler.status() if night_scheduler else {"enabled": False, "running": False},
            "sovereignty": sovereignty_status(),
            "integrations": integration_status(),
        }
    uni = p.expander.get_status()
    fin = p.finance_status()
    cur = p.curiosity.get_status()
    return {
        "brand": "MKAOS",
        "version": "6.5",
        "status": "ok",
        "sovereignty": sovereignty_status(),
        "integrations": integration_status(),
        "ollama": _ollama_status(p),
        "rag": p.memory.stats(),
        "user": user,
        "assistant": p.status(),
        "universe": uni,
        "curiosity": cur,
        "energy": policy_status(),
        "models": p.router.info(),
        "jobs": job_bus.list_recent(8, owner_id=user["username"]),
        "finance": {
            "equity": fin.get("equity"),
            "pnl_total_pct": fin.get("pnl_total_pct"),
            "open_count": len(fin.get("open_positions", [])),
            "mode": fin.get("mode"),
            "circuit_breaker": fin.get("circuit_breaker"),
        },
        "pending_approvals": len(p.permissions.list_pending()),
        "github_enabled": p.github.enabled,
        "chat_turns": len(chat_history.get(user["username"], [])),
        "privacy": {
            "web_research": os.getenv("ALLOW_WEB_RESEARCH", "false").lower() == "true",
            "external_finance_data": os.getenv("ALLOW_EXTERNAL_FINANCE_DATA", "false").lower() == "true",
            "site_scanning": os.getenv("ALLOW_SITE_SCANNING", "false").lower() == "true",
            "external_notifications": os.getenv("ALLOW_EXTERNAL_NOTIFICATIONS", "false").lower() == "true",
            "github_network_access": p.github.enabled,
        },
        "night_scheduler": night_scheduler.status() if night_scheduler else {"enabled": False, "running": False},
    }


@app.get("/api/jobs")
async def api_jobs(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    return {"jobs": job_bus.list_recent(30, owner_id=user["username"])}


@app.get("/api/jobs/stream")
async def api_jobs_stream(authorization: Optional[str] = Header(None)):
    """SSE — canlı iş güncellemeleri."""
    user = get_user(authorization)
    q: queue.Queue = queue.Queue()

    owner_id = str(user["username"]).strip().lower()
    def on_event(payload: dict):
        if str(payload.get("owner_id", "")).strip().lower() == owner_id:
            q.put(payload)

    job_bus.subscribe(on_event)

    async def gen():
        # snapshot
        for j in job_bus.list_recent(10, owner_id=user["username"]):
            yield f"data: {json.dumps(j, ensure_ascii=False)}\n\n"
        while True:
            try:
                item = await asyncio.get_event_loop().run_in_executor(None, lambda: q.get(timeout=15))
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
            except Exception:
                yield ": keepalive\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/chat")
async def api_chat(req: ChatRequest, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    message = req.message.strip()
    if not message:
        return {"reply": "Boş mesaj."}
    backend = os.getenv("MKAOS_CHAT_BACKEND", "native-rust").strip().lower()
    try:
        if message.lower() in ("/status", "durum", "status"):
            reply = get_pipeline(user["username"]).status()
        elif backend == "native-rust":
            # Never disguise an absent model as generated text or silently call third-party weights.
            readiness = native_model_readiness()
            if not readiness["ready"]:
                return {
                    "reply": (
                        "MKAOS yerel sohbet modeli henüz hazır değil. "
                        + str(readiness["message"])
                        + " Kurulum adımlarını ve model doğrulama gereksinimlerini README.md içinden kontrol et. "
                        + "Bu mesaj model tarafından üretilmedi; üçüncü taraf modele veri gönderilmedi."
                    ),
                    "status": "setup_required",
                    "model_readiness": readiness["status"],
                }
            reply = generate_native_reply(message)
        elif backend == "legacy-smollm":
            # Explicit compatibility escape hatch; enable only when deliberately accepted.
            reply = get_pipeline(user["username"]).chat(message)
        else:
            raise HTTPException(503, "Bilinmeyen MKAOS_CHAT_BACKEND; native-rust veya legacy-smollm seç.")
    except HTTPException:
        raise
    except NativeMkaosUnavailable as exc:
        logger.warning("Native MKAOS sohbeti hazır değil (%s).", type(exc).__name__)
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        logger.warning("Sohbet yanıtı üretilemedi (%s).", type(exc).__name__)
        raise HTTPException(503, "Seçili sohbet motoru şu anda yanıt üretemiyor; yerel yapılandırmayı ve günlükleri kontrol et.") from exc
    history = chat_history.setdefault(user["username"], [])
    from datetime import datetime
    history.extend([
        {"role": "user", "content": message, "timestamp": datetime.now().astimezone().isoformat()},
        {"role": "assistant", "content": reply, "timestamp": datetime.now().astimezone().isoformat()},
    ])
    if len(history) > 300:
        del history[:-300]
    _save_chat_history()
    return {"reply": reply}


@app.get("/api/history")
async def api_history(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    return {"history": chat_history.get(user["username"], [])[-50:]}


@app.post("/api/expand")
async def api_expand(req: ExpandRequest, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    p = get_pipeline(user["username"])
    if req.topic:
        p.expander.add_seed_topic(req.topic)

    def work(upd):
        upd(progress=0.2, message="Aranıyor...")
        result = p.expand_knowledge(topic=req.topic)
        upd(progress=0.9, message=f"+{result.get('pages_ingested', 0)} sayfa")
        return result

    jid = job_bus.run_in_thread("expand", f"Bilgi: {req.topic or 'otomatik'}", work, owner_id=user["username"])
    return {"status": "started", "job_id": jid, "message": "Bilgi genişletme başladı"}


@app.post("/api/seed")
async def api_seed(req: SeedRequest, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    get_pipeline(user["username"]).expander.add_seed_topic(req.topic)
    return {"status": "ok"}


@app.get("/api/universe")
async def api_universe(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    return get_pipeline(user["username"]).expander.get_status()


@app.post("/api/curiosity")
async def api_curiosity(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    p = get_pipeline(user["username"])

    def work(upd):
        upd(progress=0.3, message="Merak konusu seçiliyor")
        r = p.run_curiosity()
        upd(progress=0.95, message=r.get("topic", ""))
        return r

    jid = job_bus.run_in_thread("curiosity", "Merak turu", work, owner_id=user["username"])
    return {"status": "started", "job_id": jid}


@app.get("/api/curiosity")
async def api_curiosity_status(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    return get_pipeline(user["username"]).curiosity.get_status()


@app.get("/api/discover")
async def api_discover(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    data = get_pipeline(user["username"]).discover_local()
    return {"result": data, "report": get_pipeline(user["username"]).local_discovery.format_report(data)}


@app.post("/api/legacy")
async def api_legacy(req: LegacyRequest, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    if len(req.passphrase) < 8:
        raise HTTPException(400, "Parola en az 8 karakter")
    return {"status": "ok", "message": get_pipeline(user["username"]).legacy_export(req.passphrase)}


@app.post("/api/night")
async def api_night(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    p = get_pipeline(user["username"])

    def work(upd):
        upd(progress=0.2, message="Gece araştırması")
        r = p.run_night_research()
        upd(progress=0.95, message="Rapor yazıldı")
        return {"summary": (r.get("summary") or "")[:2000]}

    jid = job_bus.run_in_thread("night", "Gece araştırması", work, owner_id=user["username"])
    return {"status": "started", "job_id": jid}


@app.post("/api/podcast")
async def api_podcast(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    return get_pipeline(user["username"]).podcast_from_night()


@app.post("/api/plan")
async def api_plan(req: PlanRequest, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    return get_pipeline(user["username"]).create_plan(req.goal)


@app.post("/api/plan/{plan_id}/run")
async def api_plan_run(plan_id: str, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    p = get_pipeline(user["username"])

    def work(upd):
        upd(progress=0.2, message="Güvenli adımlar çalışıyor")
        r = p.run_plan_safe(plan_id)
        upd(progress=0.95, message="Bitti")
        return r

    jid = job_bus.run_in_thread("plan", f"Plan {plan_id}", work, owner_id=user["username"])
    return {"status": "started", "job_id": jid}


@app.get("/api/plans")
async def api_plans(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    return {"plans": get_pipeline(user["username"]).planner.list_plans(12)}


@app.post("/api/pack")
async def api_pack(req: PackRequest, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    return get_pipeline(user["username"]).export_knowledge_pack(title=req.title or "MKAOS Araştırma Paketi")


@app.post("/api/ingest")
async def api_ingest(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    suffix = Path(file.filename or "doc.txt").suffix.lower()
    if suffix not in {".pdf", ".md", ".txt", ".csv"}:
        raise HTTPException(400, "Sadece PDF, MD, TXT, CSV")
    max_bytes = 20 * 1024 * 1024
    tenant_upload_dir = tenant_root("./memory/uploads", tenant_storage_id(user["username"]))
    tenant_upload_dir.mkdir(parents=True, exist_ok=True)
    dest = tenant_upload_dir / f"{uuid.uuid4().hex}{suffix}"
    total = 0
    try:
        with dest.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(413, "Dosya en fazla 20 MB olabilir.")
                f.write(chunk)
        return get_pipeline(user["username"]).ingest_document(str(dest))
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


@app.get("/api/approvals")
async def api_approvals(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    if user.get("role") != "owner":
        raise HTTPException(403, "Onay içeriği ve denetim geçmişi yalnızca sahibine açıktır.")
    permissions = get_pipeline(user["username"]).permissions
    return {"pending": permissions.list_actionable(), "history": permissions.list_history(30)}


@app.post("/api/approvals/{request_id}/approve")
async def api_approve(request_id: str, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    if user.get("role") != "owner":
        raise HTTPException(403, "Yalnızca sahip onay verebilir.")
    return {"success": get_pipeline(user["username"]).permissions.approve(request_id)}


@app.post("/api/approvals/{request_id}/execute")
async def api_execute_approved(request_id: str, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    if user.get("role") != "owner":
        raise HTTPException(403, "Yalnızca sahip onaylı işlemi yürütebilir.")
    p = get_pipeline(user["username"])
    request = p.permissions.get_request(request_id)
    if not request or request.get("status") != "approved":
        raise HTTPException(409, "İşlem bulunamadı veya yürütme için onaylı değil.")
    if request.get("action") not in {"open_github_issue", "create_pull_request", "modify_files", "push_to_remote"}:
        raise HTTPException(400, "Bu işlem türü henüz güvenli yürütücüde desteklenmiyor.")
    if not p.permissions.begin_execution(request_id):
        raise HTTPException(409, "İşlem zaten yürütülüyor veya daha önce tüketildi.")
    request = p.permissions.get_request(request_id) or {}
    try:
        result = p.github.execute_approved_request(request)
        final_status = "staged" if request.get("action") == "modify_files" else "executed"
        p.permissions.finish_execution(request_id, True, result, final_status=final_status)
        return {"success": True, "result": result}
    except Exception as exc:
        # Do not automatically retry: a network timeout can leave the remote outcome unknown.
        message = f"Yürütme başarısız veya sonucu belirsiz ({type(exc).__name__}); tekrar denemeden önce GitHub'ı kontrol et."
        p.permissions.finish_execution(request_id, False, message)
        raise HTTPException(502, message)


@app.post("/api/approvals/{request_id}/reject")
async def api_reject(request_id: str, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    if user.get("role") != "owner":
        raise HTTPException(403, "Yalnızca sahip reddedebilir.")
    return {"success": get_pipeline(user["username"]).permissions.reject(request_id)}


@app.get("/api/github/repos")
async def api_github_repos(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    if user.get("role") != "owner":
        raise HTTPException(403, "GitHub depoları yalnızca sahibine açıktır.")
    p = get_pipeline(user["username"])
    if not p.github.enabled:
        return {"error": "GITHUB_TOKEN yok", "repos": []}
    return {"repos": p.github.list_repos(20)}


@app.post("/api/finance")
async def api_finance(req: FinanceRequest, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    return {"result": get_pipeline(user["username"]).finance.analyze(req.query)}


@app.get("/api/finance/portfolio")
async def api_finance_portfolio(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    return get_pipeline(user["username"]).finance_status()


@app.post("/api/finance/cycle")
async def api_finance_cycle(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    p = get_pipeline(user["username"])

    def work(upd):
        upd(progress=0.3, message="Paper döngü")
        r = p.run_finance_cycle()
        return r.get("decision")

    jid = job_bus.run_in_thread("finance", "Paper trading", work, owner_id=user["username"])
    return {"status": "started", "job_id": jid}


@app.post("/api/image")
async def api_image(req: ImageRequest, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    try:
        p = get_pipeline(user["username"])
        if p.media_engine.should_defer_heavy():
            return p.media_engine.submit("generate", {"prompt": req.prompt[:2000], "width": req.width, "height": req.height})
        return await asyncio.to_thread(p.media_bridge.execute, "generate", {"prompt": req.prompt, "width": req.width, "height": req.height})
    except Exception as exc:
        from tools.image_gen import MediaToolError
        if isinstance(exc, MediaToolError):
            raise HTTPException(503, str(exc))
        logger.exception("MKAOS local image generation failed")
        raise HTTPException(500, "Yerel görsel üretimi başarısız oldu.")


@app.post("/api/media/edit")
async def api_media_edit(prompt: str = Form(...), file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    raw = await file.read(12 * 1024 * 1024 + 1)
    if len(raw) > 12 * 1024 * 1024:
        raise HTTPException(413, "Görsel en fazla 12 MB olabilir.")
    try:
        p = get_pipeline(user["username"])
        if p.media_engine.should_defer_heavy():
            tenant_upload_dir = tenant_root("./memory/uploads", user["username"])
            tenant_upload_dir.mkdir(parents=True, exist_ok=True)
            saved = tenant_upload_dir / ("media_" + uuid.uuid4().hex + ".upload")
            saved.write_bytes(raw)
            return p.media_engine.submit("edit", {"prompt": prompt[:2000], "image_path": str(saved.resolve())})
        return await asyncio.to_thread(p.media_bridge.execute, "edit", {"prompt": prompt, "image_bytes": raw})
    except Exception as exc:
        from tools.image_gen import MediaToolError
        if isinstance(exc, MediaToolError):
            raise HTTPException(503, str(exc))
        logger.exception("MKAOS local image editing failed")
        raise HTTPException(500, "Görsel düzenleme başarısız oldu.")


@app.post("/api/media/background")
async def api_media_background(file: UploadFile = File(...), color: str = Form("#172033"), authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    raw = await file.read(12 * 1024 * 1024 + 1)
    if len(raw) > 12 * 1024 * 1024:
        raise HTTPException(413, "Görsel en fazla 12 MB olabilir.")
    try:
        p = get_pipeline(user["username"])
        if p.media_engine.should_defer_heavy():
            tenant_upload_dir = tenant_root("./memory/uploads", user["username"])
            tenant_upload_dir.mkdir(parents=True, exist_ok=True)
            saved = tenant_upload_dir / ("media_" + uuid.uuid4().hex + ".upload")
            saved.write_bytes(raw)
            return p.media_engine.submit("background", {"image_path": str(saved.resolve()), "color": color})
        return await asyncio.to_thread(p.media_bridge.execute, "background", {"image_bytes": raw, "color": color})
    except Exception as exc:
        from tools.image_gen import MediaToolError
        if isinstance(exc, MediaToolError):
            raise HTTPException(503, str(exc))
        logger.exception("MKAOS local background replacement failed")
        raise HTTPException(500, "Arka plan değiştirme başarısız oldu.")


class VideoRequest(BaseModel):
    filename: str
    duration: float = 4.0


class VideoStoryRequest(BaseModel):
    prompts: list[str]
    duration: float = 8.0


class ImprovementProposalRequest(BaseModel):
    title: str
    rationale: str
    files: list[str]
    patch: str
    test_plan: list[str]


class ImprovementGenerateRequest(BaseModel):
    file_path: str
    issue: str
    test_plan: list[str]


class ImprovementApprovalRequest(BaseModel):
    confirmation: str


@app.post("/api/media/video")
async def api_media_video(req: VideoRequest, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    try:
        p = get_pipeline(user["username"])
        if p.media_engine.should_defer_heavy():
            return p.media_engine.submit("video", {"filename": req.filename, "duration": req.duration})
        return await asyncio.to_thread(p.media_bridge.execute, "video", {"filename": req.filename, "duration": req.duration})
    except Exception as exc:
        from tools.image_gen import MediaToolError
        if isinstance(exc, MediaToolError):
            raise HTTPException(503, str(exc))
        logger.exception("MKAOS local video rendering failed")
        raise HTTPException(500, "Video oluşturma başarısız oldu.")


@app.post("/api/media/story-video")
async def api_media_story_video(req: VideoStoryRequest, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    if not isinstance(req.prompts, list) or not 2 <= len(req.prompts) <= 6:
        raise HTTPException(400, "Storyboard için 2-6 sahne açıklaması gerekli.")
    if any(not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 1000 for prompt in req.prompts):
        raise HTTPException(400, "Her sahne açıklaması 1-1000 karakter olmalı.")
    duration = max(4.0, min(24.0, float(req.duration)))
    try:
        p = get_pipeline(user["username"])
        payload = {"prompts": [prompt.strip() for prompt in req.prompts], "duration": duration}
        if p.media_engine.should_defer_heavy():
            return p.media_engine.submit("story_video", payload)
        return await asyncio.to_thread(p.media_bridge.execute, "story_video", payload)
    except Exception as exc:
        from tools.image_gen import MediaToolError
        if isinstance(exc, MediaToolError):
            raise HTTPException(503, str(exc))
        logger.exception("MKAOS local storyboard video failed")
        raise HTTPException(500, "Storyboard videosu oluşturulamadı.")


@app.get("/api/images/{filename}")
async def serve_image(filename: str, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}\.(png|jpg|jpeg|webp|mp4)", filename, re.IGNORECASE):
        raise HTTPException(404)
    root = (tenant_root("./memory/tenants", tenant_storage_id(user["username"])) / "generated_images").resolve()
    path = (root / filename).resolve()
    if root in path.parents and path.is_file():
        return FileResponse(path, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
    raise HTTPException(404)


@app.get("/api/sovereignty")
async def api_sovereignty(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    return sovereignty_status()


@app.get("/api/media/capabilities")
async def api_media_capabilities(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    p = get_pipeline(user["username"])
    return {"bridge": p.media_bridge.capabilities(), "engine": p.media_engine.capabilities(),
            "jobs": p.media_engine.list_jobs(20), "video_mode": "local ffmpeg motion effect plus 2-6-scene self-hosted Stable Diffusion storyboard; not neural text-to-video"}


@app.post("/api/media/queue")
async def api_media_queue(req: MediaQueueRequest, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    if req.operation != "generate":
        raise HTTPException(400, "Kuyruğa şu an yalnızca metinden görsel üretim görevi alınır.")
    try:
        return get_pipeline(user["username"]).media_engine.submit("generate", {"prompt": req.prompt[:2000],
            "width": req.width, "height": req.height})
    except Exception as exc:
        raise HTTPException(400, str(exc))


@app.post("/api/media/jobs/{job_id}/run")
async def api_media_run_job(job_id: str, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    try:
        return await asyncio.to_thread(get_pipeline(user["username"]).media_engine.run_job, job_id)
    except Exception as exc:
        raise HTTPException(400, str(exc))


@app.get("/api/media/jobs")
async def api_media_jobs(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    return {"jobs": get_pipeline(user["username"]).media_engine.list_jobs(30)}


def _improvement_store(username: str) -> ImprovementProposalStore:
    root = tenant_root("./memory/tenants", tenant_storage_id(username)) / "improvement_proposals"
    return ImprovementProposalStore(root)


@app.post("/api/improvements/generate")
async def api_generate_improvement_proposal(req: ImprovementGenerateRequest, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    file_path = str(req.file_path or "").strip().replace("\\", "/")
    try:
        # Validate the requested path before reading any repository file.
        from core.improvement_gate import validate_candidate
        validate_candidate(title="Code improvement", rationale=req.issue, files=[file_path],
                           patch="candidate", test_plan=req.test_plan)
        source = (ROOT / file_path).resolve()
        if ROOT not in source.parents or not source.is_file() or source.stat().st_size > 40000:
            raise ImprovementProposalError("Yalnızca izin verilen, 40 KB altındaki mevcut kaynak dosyalar seçilebilir.")
        issue = str(req.issue or "").strip()
        if not issue or len(issue) > 2000:
            raise ImprovementProposalError("Sorun açıklaması 1-2000 karakter olmalı.")
        current = source.read_text(encoding="utf-8")
        pipeline = get_pipeline(user["username"])
        candidate = await asyncio.to_thread(pipeline.code_writer.propose_fix, file_path, current, issue)
        if not isinstance(candidate, str) or not candidate.strip() or len(candidate.encode("utf-8")) > 40000:
            raise ImprovementProposalError("Yerel model boş veya çok büyük bir kod önerisi döndürdü.")
        diff = "\n".join(difflib.unified_diff(
            current.splitlines(), candidate.strip().splitlines(),
            fromfile="a/" + file_path, tofile="b/" + file_path, lineterm=""
        ))
        if not diff.strip():
            raise ImprovementProposalError("Model değişiklik önermedi; dosya aynı kaldı.")
        return _improvement_store(user["username"]).create(
            title="Kod iyileştirmesi: " + file_path,
            rationale=issue,
            files=[file_path],
            patch=diff,
            test_plan=req.test_plan,
        )
    except ImprovementProposalError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        logger.warning("Local code proposal generation failed: %s", type(exc).__name__)
        raise HTTPException(503, "Yerel kod önerisi üretilemedi; Ollama/model durumunu denetle.")


@app.post("/api/improvements/proposals")
async def api_create_improvement_proposal(req: ImprovementProposalRequest, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    try:
        return _improvement_store(user["username"]).create(
            title=req.title, rationale=req.rationale, files=req.files, patch=req.patch, test_plan=req.test_plan
        )
    except ImprovementProposalError as exc:
        raise HTTPException(400, str(exc))


@app.get("/api/improvements/proposals")
async def api_list_improvement_proposals(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    return {"proposals": _improvement_store(user["username"]).list()}


@app.get("/api/improvements/proposals/{proposal_id}")
async def api_get_improvement_proposal(proposal_id: str, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    try:
        return _improvement_store(user["username"]).get(proposal_id)
    except ImprovementProposalError as exc:
        raise HTTPException(404, str(exc))


@app.post("/api/improvements/proposals/{proposal_id}/approve")
async def api_approve_improvement_proposal(proposal_id: str, req: ImprovementApprovalRequest,
                                           authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    try:
        return _improvement_store(user["username"]).approve_for_review(proposal_id, req.confirmation)
    except ImprovementProposalError as exc:
        raise HTTPException(400, str(exc))


@app.post("/api/approval/verify")
async def api_approval_verify(req: ApprovalVerifyRequest, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    try:
        result = SignedApprovalProtocol().verify(req.payload, req.signature_b64)
        return {**result, "execution": "not_started", "message": "İmza doğrulandı; bu uç nokta push/merge yürütmez."}
    except ApprovalProtocolError as exc:
        raise HTTPException(400, str(exc))



@app.post("/api/privacy/forget")
async def api_privacy_forget(req: ForgetRequest, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    if req.confirmation != "DELETE_MATCHING_MEMORY":
        raise HTTPException(400, "Açık onay gerekli: DELETE_MATCHING_MEMORY")
    if len(req.topic.strip()) < 3:
        raise HTTPException(400, "Silme konusu en az 3 karakter olmalı.")
    p = get_pipeline(user["username"])
    try:
        memory_result = p.personal_memory.forget_matching(req.topic, req.last_hours)
    except Exception as exc:
        logger.warning("Personal memory deletion failed: %s", type(exc).__name__)
        raise HTTPException(500, "Kişisel vektör hafızası temizlenemedi; veri otomatik sıfırlanmadı.")
    history = chat_history.get(user["username"], [])
    phrase = req.topic.strip().casefold()
    from datetime import datetime, timezone
    cutoff = datetime.now(timezone.utc).timestamp() - max(1, min(req.last_hours, 8760)) * 3600
    def is_recent_match(row):
        if phrase not in str(row.get("content", "")).casefold():
            return False
        stamp = row.get("timestamp")
        if not stamp:
            return False
        try:
            parsed = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp() >= cutoff
        except (TypeError, ValueError, OverflowError):
            return False
    before = len(history)
    chat_history[user["username"]] = [row for row in history if not is_recent_match(row)]
    deleted_chat_turns = before - len(chat_history[user["username"]])
    if deleted_chat_turns:
        _save_chat_history()
    audit = tenant_root("./memory/tenants", user["username"]) / "privacy_deletion_audit.jsonl"
    audit.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    import hashlib
    record = {"timestamp": datetime.now().astimezone().isoformat(),
              "username": str(user.get("username", "owner")),
              "topic_sha256": hashlib.sha256(req.topic.strip().encode()).hexdigest(),
              "last_hours": max(1, min(req.last_hours, 8760)),
              "deleted_chat_turns": deleted_chat_turns, "result": "local_match_delete_attempted"}
    fd = os.open(str(audit), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\\n")
        handle.flush()
        os.fsync(handle.fileno())
    return {"success": True, **memory_result, "deleted_chat_turns": deleted_chat_turns,
            "audit_recorded": True, "limitations": memory_result["limitations"]}


@app.get("/api/audit/clean-room")
async def api_clean_room_audit(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    return scan_code_cleanliness(os.getenv("MKAOS_AUDIT_ROOT", "."), max_files=300)


@app.get("/api/users")
async def api_users(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    if user.get("role") not in ("owner", "admin"):
        raise HTTPException(403)
    return {"users": auth.list_users()}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("WEB_PORT", "8000"))
    uvicorn.run("web.app:app", host="0.0.0.0", port=port, reload=False)

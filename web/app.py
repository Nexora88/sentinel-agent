"""
SEKA v6 — Sentinel Egemen Kişisel Ajan
Canlı işler · plan motoru · bilgi paketleri · Ollama
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Request, Header, HTTPException, UploadFile, File
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
from core.auth import AuthManager
from core.energy_policy import policy_status
from core.job_bus import job_bus
from core.local_voice import LocalVoiceError, voice_status, synthesize as synthesize_local_voice, transcribe as transcribe_local_voice

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seka.web")

app = FastAPI(title="SEKA", version="6.1", description="Sentinel Egemen Kişisel Ajan")

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
UPLOAD_DIR = Path("./memory/uploads")
for d in (TEMPLATES_DIR, STATIC_DIR, UPLOAD_DIR):
    d.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

pipeline: Optional[SentinelPipeline] = None
auth = AuthManager()
CHAT_HISTORY_FILE = Path("./memory/chat_history.json")


def _load_chat_history() -> dict:
    if not CHAT_HISTORY_FILE.exists():
        return {}
    try:
        data = json.loads(CHAT_HISTORY_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or any(not isinstance(v, list) for v in data.values()):
            raise ValueError("chat history must be a user-to-list mapping")
        return data
    except Exception as exc:
        # Preserve user data and stop rather than silently resetting corrupted history.
        raise RuntimeError(
            f"Chat history is unreadable; preserve and recover {CHAT_HISTORY_FILE} before restarting."
        ) from exc


def _save_chat_history() -> None:
    CHAT_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
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
    "name": "SEKA",
    "version": "6.1",
    "tagline": "Yerel Türkçe ajan — ağ özellikleri varsayılan olarak kapalı",
    "pillars": [
        "Ollama ile tamamen yerel zeka",
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


def get_pipeline() -> SentinelPipeline:
    global pipeline
    if pipeline is None:
        pipeline = SentinelPipeline()
    return pipeline


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

class ImageRequest(BaseModel):
    prompt: str

class FinanceRequest(BaseModel):
    query: str

class LegacyRequest(BaseModel):
    passphrase: str

class PlanRequest(BaseModel):
    goal: str

class PackRequest(BaseModel):
    title: Optional[str] = "SEKA Araştırma Paketi"

class VoiceRequest(BaseModel):
    text: str
    voice: str = "male"
    cat_mode: bool = False


@app.on_event("startup")
async def startup():
    logger.info("SEKA Web v6.1")
    get_pipeline()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/manifesto")
async def api_manifesto():
    return MANIFESTO


@app.post("/api/login")
async def login(req: LoginRequest):
    token = auth.authenticate(req.username, req.password)
    if not token:
        raise HTTPException(401, "Hatalı kullanıcı veya şifre")
    return {"token": token, "user": auth.validate(token)}


@app.get("/api/voice/status")
async def api_voice_status(authorization: Optional[str] = Header(None)):
    get_user(authorization)
    return voice_status()


@app.post("/api/voice/synthesize")
async def api_voice_synthesize(req: VoiceRequest, authorization: Optional[str] = Header(None)):
    get_user(authorization)
    try:
        audio = synthesize_local_voice(req.text, req.voice, req.cat_mode)
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


@app.get("/api/status")
async def api_status(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    p = get_pipeline()
    uni = p.expander.get_status()
    fin = p.finance_status()
    cur = p.curiosity.get_status()
    return {
        "brand": "SEKA",
        "version": "6.1",
        "user": user,
        "assistant": p.status(),
        "universe": uni,
        "curiosity": cur,
        "energy": policy_status(),
        "models": p.router.info(),
        "jobs": job_bus.list_recent(8),
        "finance": {
            "equity": fin.get("equity"),
            "pnl_total_pct": fin.get("pnl_total_pct"),
            "open_count": len(fin.get("open_positions", [])),
            "mode": fin.get("mode"),
            "circuit_breaker": fin.get("circuit_breaker"),
        },
        "pending_approvals": len(p.permissions.list_pending()),
        "github_enabled": p.github.enabled,
        "chat_turns": sum(len(turns) for turns in chat_history.values()),
        "privacy": {
            "web_research": os.getenv("ALLOW_WEB_RESEARCH", "false").lower() == "true",
            "external_finance_data": os.getenv("ALLOW_EXTERNAL_FINANCE_DATA", "false").lower() == "true",
            "site_scanning": os.getenv("ALLOW_SITE_SCANNING", "false").lower() == "true",
            "external_notifications": os.getenv("ALLOW_EXTERNAL_NOTIFICATIONS", "false").lower() == "true",
            "github_network_access": p.github.enabled,
        },
    }


@app.get("/api/jobs")
async def api_jobs(authorization: Optional[str] = Header(None)):
    get_user(authorization)
    return {"jobs": job_bus.list_recent(30)}


@app.get("/api/jobs/stream")
async def api_jobs_stream(authorization: Optional[str] = Header(None)):
    """SSE — canlı iş güncellemeleri."""
    get_user(authorization)
    q: queue.Queue = queue.Queue()

    def on_event(payload: dict):
        q.put(payload)

    job_bus.subscribe(on_event)

    async def gen():
        # snapshot
        for j in job_bus.list_recent(10):
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
    p = get_pipeline()
    message = req.message.strip()
    if not message:
        return {"reply": "Boş mesaj."}
    if message.lower() in ("/status", "durum", "status"):
        reply = p.status()
    else:
        reply = p.chat(message)
    history = chat_history.setdefault(user["username"], [])
    history.extend([
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
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
    get_user(authorization)
    p = get_pipeline()
    if req.topic:
        p.expander.add_seed_topic(req.topic)

    def work(upd):
        upd(progress=0.2, message="Aranıyor...")
        result = p.expand_knowledge(topic=req.topic)
        upd(progress=0.9, message=f"+{result.get('pages_ingested', 0)} sayfa")
        return result

    jid = job_bus.run_in_thread("expand", f"Bilgi: {req.topic or 'otomatik'}", work)
    return {"status": "started", "job_id": jid, "message": "Bilgi genişletme başladı"}


@app.post("/api/seed")
async def api_seed(req: SeedRequest, authorization: Optional[str] = Header(None)):
    get_user(authorization)
    get_pipeline().expander.add_seed_topic(req.topic)
    return {"status": "ok"}


@app.get("/api/universe")
async def api_universe(authorization: Optional[str] = Header(None)):
    get_user(authorization)
    return get_pipeline().expander.get_status()


@app.post("/api/curiosity")
async def api_curiosity(authorization: Optional[str] = Header(None)):
    get_user(authorization)
    p = get_pipeline()

    def work(upd):
        upd(progress=0.3, message="Merak konusu seçiliyor")
        r = p.run_curiosity()
        upd(progress=0.95, message=r.get("topic", ""))
        return r

    jid = job_bus.run_in_thread("curiosity", "Merak turu", work)
    return {"status": "started", "job_id": jid}


@app.get("/api/curiosity")
async def api_curiosity_status(authorization: Optional[str] = Header(None)):
    get_user(authorization)
    return get_pipeline().curiosity.get_status()


@app.get("/api/discover")
async def api_discover(authorization: Optional[str] = Header(None)):
    get_user(authorization)
    data = get_pipeline().discover_local()
    return {"result": data, "report": get_pipeline().local_discovery.format_report(data)}


@app.post("/api/legacy")
async def api_legacy(req: LegacyRequest, authorization: Optional[str] = Header(None)):
    get_user(authorization)
    if len(req.passphrase) < 8:
        raise HTTPException(400, "Parola en az 8 karakter")
    return {"status": "ok", "message": get_pipeline().legacy_export(req.passphrase)}


@app.post("/api/night")
async def api_night(authorization: Optional[str] = Header(None)):
    get_user(authorization)
    p = get_pipeline()

    def work(upd):
        upd(progress=0.2, message="Gece araştırması")
        r = p.run_night_research()
        upd(progress=0.95, message="Rapor yazıldı")
        return {"summary": (r.get("summary") or "")[:2000]}

    jid = job_bus.run_in_thread("night", "Gece araştırması", work)
    return {"status": "started", "job_id": jid}


@app.post("/api/podcast")
async def api_podcast(authorization: Optional[str] = Header(None)):
    get_user(authorization)
    return get_pipeline().podcast_from_night()


@app.post("/api/plan")
async def api_plan(req: PlanRequest, authorization: Optional[str] = Header(None)):
    get_user(authorization)
    return get_pipeline().create_plan(req.goal)


@app.post("/api/plan/{plan_id}/run")
async def api_plan_run(plan_id: str, authorization: Optional[str] = Header(None)):
    get_user(authorization)
    p = get_pipeline()

    def work(upd):
        upd(progress=0.2, message="Güvenli adımlar çalışıyor")
        r = p.run_plan_safe(plan_id)
        upd(progress=0.95, message="Bitti")
        return r

    jid = job_bus.run_in_thread("plan", f"Plan {plan_id}", work)
    return {"status": "started", "job_id": jid}


@app.get("/api/plans")
async def api_plans(authorization: Optional[str] = Header(None)):
    get_user(authorization)
    return {"plans": get_pipeline().planner.list_plans(12)}


@app.post("/api/pack")
async def api_pack(req: PackRequest, authorization: Optional[str] = Header(None)):
    get_user(authorization)
    return get_pipeline().export_knowledge_pack(title=req.title or "SEKA Araştırma Paketi")


@app.post("/api/ingest")
async def api_ingest(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    get_user(authorization)
    suffix = Path(file.filename or "doc.txt").suffix.lower()
    if suffix not in {".pdf", ".md", ".txt", ".csv"}:
        raise HTTPException(400, "Sadece PDF, MD, TXT, CSV")
    max_bytes = 20 * 1024 * 1024
    dest = UPLOAD_DIR / f"{uuid.uuid4().hex[:12]}{suffix}"
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
        return get_pipeline().ingest_document(str(dest))
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
    permissions = get_pipeline().permissions
    return {"pending": permissions.list_actionable(), "history": permissions.list_history(30)}


@app.post("/api/approvals/{request_id}/approve")
async def api_approve(request_id: str, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    if user.get("role") != "owner":
        raise HTTPException(403, "Yalnızca sahip onay verebilir.")
    return {"success": get_pipeline().permissions.approve(request_id)}


@app.post("/api/approvals/{request_id}/execute")
async def api_execute_approved(request_id: str, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    if user.get("role") != "owner":
        raise HTTPException(403, "Yalnızca sahip onaylı işlemi yürütebilir.")
    p = get_pipeline()
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
    return {"success": get_pipeline().permissions.reject(request_id)}


@app.get("/api/github/repos")
async def api_github_repos(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    if user.get("role") != "owner":
        raise HTTPException(403, "GitHub depoları yalnızca sahibine açıktır.")
    p = get_pipeline()
    if not p.github.enabled:
        return {"error": "GITHUB_TOKEN yok", "repos": []}
    return {"repos": p.github.list_repos(20)}


@app.post("/api/finance")
async def api_finance(req: FinanceRequest, authorization: Optional[str] = Header(None)):
    get_user(authorization)
    return {"result": get_pipeline().finance.analyze(req.query)}


@app.get("/api/finance/portfolio")
async def api_finance_portfolio(authorization: Optional[str] = Header(None)):
    get_user(authorization)
    return get_pipeline().finance_status()


@app.post("/api/finance/cycle")
async def api_finance_cycle(authorization: Optional[str] = Header(None)):
    get_user(authorization)
    p = get_pipeline()

    def work(upd):
        upd(progress=0.3, message="Paper döngü")
        r = p.run_finance_cycle()
        return r.get("decision")

    jid = job_bus.run_in_thread("finance", "Paper trading", work)
    return {"status": "started", "job_id": jid}


@app.post("/api/image")
async def api_image(req: ImageRequest, authorization: Optional[str] = Header(None)):
    get_user(authorization)
    return get_pipeline().image_gen.generate(req.prompt)


@app.get("/api/images/{filename}")
async def serve_image(filename: str):
    path = Path("./memory/generated_images") / filename
    if path.exists():
        return FileResponse(path)
    raise HTTPException(404)


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

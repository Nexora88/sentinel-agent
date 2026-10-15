"""
SEKA — Sentinel Egemen Kişisel Ajan
Yerel · Türkçe · Ollama · ücretli API yok
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Request, BackgroundTasks, Header, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seka.web")

app = FastAPI(title="SEKA", version="4.0", description="Sentinel Egemen Kişisel Ajan")

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
UPLOAD_DIR = Path("./memory/uploads")
TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

pipeline: Optional[SentinelPipeline] = None
auth = AuthManager()
chat_history: List[dict] = []


def get_pipeline() -> SentinelPipeline:
    global pipeline
    if pipeline is None:
        pipeline = SentinelPipeline()
    return pipeline


def get_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        if os.getenv("AUTH_REQUIRED", "false").lower() != "true":
            return {"username": "owner", "role": "owner", "display_name": "Sahip"}
        raise HTTPException(401, "Yetki gerekli")
    token = authorization.replace("Bearer ", "").strip()
    session = auth.validate(token)
    if not session:
        raise HTTPException(401, "Geçersiz veya süresi dolmuş oturum")
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


@app.on_event("startup")
async def startup():
    logger.info("SEKA Web v4.0 başlıyor...")
    get_pipeline()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/login")
async def login(req: LoginRequest):
    token = auth.authenticate(req.username, req.password)
    if not token:
        raise HTTPException(401, "Hatalı kullanıcı veya şifre")
    session = auth.validate(token)
    return {"token": token, "user": session}


@app.get("/api/status")
async def api_status(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    p = get_pipeline()
    uni = p.expander.get_status()
    fin = p.finance_status()
    cur = p.curiosity.get_status()
    return {
        "brand": "SEKA",
        "version": "4.0",
        "user": user,
        "assistant": p.status(),
        "universe": uni,
        "curiosity": cur,
        "energy": policy_status(),
        "finance": {
            "equity": fin.get("equity"),
            "pnl_total_pct": fin.get("pnl_total_pct"),
            "open_count": len(fin.get("open_positions", [])),
            "mode": fin.get("mode"),
            "circuit_breaker": fin.get("circuit_breaker"),
        },
        "pending_approvals": len(p.permissions.list_pending()),
        "github_enabled": p.github.enabled,
        "chat_turns": len(chat_history),
    }


@app.post("/api/chat")
async def api_chat(req: ChatRequest, authorization: Optional[str] = Header(None)):
    get_user(authorization)
    p = get_pipeline()
    message = req.message.strip()
    if not message:
        return {"reply": "Boş mesaj."}
    lower = message.lower()
    if lower in ("/status", "durum", "status"):
        reply = p.status()
    else:
        reply = p.chat(message)
    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": reply})
    if len(chat_history) > 300:
        chat_history[:] = chat_history[-300:]
    return {"reply": reply}


@app.get("/api/history")
async def api_history(authorization: Optional[str] = Header(None)):
    get_user(authorization)
    return {"history": chat_history[-50:]}


@app.post("/api/expand")
async def api_expand(req: ExpandRequest, background_tasks: BackgroundTasks, authorization: Optional[str] = Header(None)):
    get_user(authorization)
    p = get_pipeline()
    if req.topic:
        p.expander.add_seed_topic(req.topic)

    def run():
        result = p.expand_knowledge(topic=req.topic)
        logger.info(f"Expansion: {result}")

    background_tasks.add_task(run)
    return {"status": "started", "message": "Bilgi evreni genişliyor..."}


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
async def api_curiosity(background_tasks: BackgroundTasks, authorization: Optional[str] = Header(None)):
    get_user(authorization)
    p = get_pipeline()

    def run():
        r = p.run_curiosity()
        logger.info(f"Curiosity: {r.get('topic')}")

    background_tasks.add_task(run)
    return {"status": "started", "message": "Merak motoru çalışıyor..."}


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
    msg = get_pipeline().legacy_export(req.passphrase)
    return {"status": "ok", "message": msg}


@app.post("/api/night")
async def api_night(background_tasks: BackgroundTasks, authorization: Optional[str] = Header(None)):
    get_user(authorization)
    p = get_pipeline()

    def run():
        r = p.run_night_research()
        logger.info("Night research done")

    background_tasks.add_task(run)
    return {"status": "started", "message": "Gece araştırması başladı (sadece öneri)."}


@app.post("/api/podcast")
async def api_podcast(authorization: Optional[str] = Header(None)):
    get_user(authorization)
    return get_pipeline().podcast_from_night()


@app.post("/api/ingest")
async def api_ingest(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
):
    get_user(authorization)
    suffix = Path(file.filename or "doc.txt").suffix.lower()
    if suffix not in {".pdf", ".md", ".txt", ".csv"}:
        raise HTTPException(400, "Sadece PDF, MD, TXT, CSV")
    safe_name = f"{uuid.uuid4().hex[:12]}{suffix}"
    dest = UPLOAD_DIR / safe_name
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    result = get_pipeline().ingest_document(str(dest))
    return result


@app.get("/api/approvals")
async def api_approvals(authorization: Optional[str] = Header(None)):
    get_user(authorization)
    return {"pending": get_pipeline().permissions.list_pending()}


@app.post("/api/approvals/{index}/approve")
async def api_approve(index: int, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    if user.get("role") not in ("owner", "admin"):
        raise HTTPException(403, "Sadece sahip/admin")
    return {"success": get_pipeline().permissions.approve(index)}


@app.post("/api/approvals/{index}/reject")
async def api_reject(index: int, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    if user.get("role") not in ("owner", "admin"):
        raise HTTPException(403, "Sadece sahip/admin")
    return {"success": get_pipeline().permissions.reject(index)}


@app.get("/api/github/repos")
async def api_github_repos(authorization: Optional[str] = Header(None)):
    get_user(authorization)
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
async def api_finance_cycle(background_tasks: BackgroundTasks, authorization: Optional[str] = Header(None)):
    get_user(authorization)
    p = get_pipeline()

    def run():
        result = p.run_finance_cycle()
        logger.info(f"Finance: {result.get('decision')}")

    background_tasks.add_task(run)
    return {"status": "started", "message": "Paper trading döngüsü (sanal para)."}


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

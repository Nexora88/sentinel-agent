"""
Sentinel Web Interface — full control panel + paper trading.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Request, BackgroundTasks, Header, HTTPException
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentinel.web")

app = FastAPI(title="Sentinel Agent", version="3.1")

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

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
            return {"username": "owner", "role": "owner", "display_name": "Owner"}
        raise HTTPException(401, "Authorization required")
    token = authorization.replace("Bearer ", "").strip()
    session = auth.validate(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
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


@app.on_event("startup")
async def startup():
    logger.info("Sentinel Web UI v3.1 starting...")
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
    return {
        "user": user,
        "assistant": p.status(),
        "universe": uni,
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
        logger.info(f"Expansion done: {result}")

    background_tasks.add_task(run)
    return {"status": "started", "message": "Bilgi genişletme başladı."}


@app.post("/api/seed")
async def api_seed(req: SeedRequest, authorization: Optional[str] = Header(None)):
    get_user(authorization)
    get_pipeline().expander.add_seed_topic(req.topic)
    return {"status": "ok"}


@app.get("/api/universe")
async def api_universe(authorization: Optional[str] = Header(None)):
    get_user(authorization)
    return get_pipeline().expander.get_status()


@app.get("/api/approvals")
async def api_approvals(authorization: Optional[str] = Header(None)):
    get_user(authorization)
    return {"pending": get_pipeline().permissions.list_pending()}


@app.post("/api/approvals/{index}/approve")
async def api_approve(index: int, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    if user.get("role") not in ("owner", "admin"):
        raise HTTPException(403, "Sadece owner/admin onaylayabilir")
    return {"success": get_pipeline().permissions.approve(index)}


@app.post("/api/approvals/{index}/reject")
async def api_reject(index: int, authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    if user.get("role") not in ("owner", "admin"):
        raise HTTPException(403, "Sadece owner/admin reddedebilir")
    return {"success": get_pipeline().permissions.reject(index)}


@app.get("/api/github/repos")
async def api_github_repos(authorization: Optional[str] = Header(None)):
    get_user(authorization)
    p = get_pipeline()
    if not p.github.enabled:
        return {"error": "GITHUB_TOKEN ayarlı değil", "repos": []}
    return {"repos": p.github.list_repos(20)}


@app.post("/api/finance")
async def api_finance(req: FinanceRequest, authorization: Optional[str] = Header(None)):
    get_user(authorization)
    return {"result": get_pipeline().finance.analyze(req.query)}


@app.get("/api/finance/portfolio")
async def api_finance_portfolio(authorization: Optional[str] = Header(None)):
    """Paper trading portfolio + thought log."""
    get_user(authorization)
    return get_pipeline().finance_status()


@app.post("/api/finance/cycle")
async def api_finance_cycle(background_tasks: BackgroundTasks, authorization: Optional[str] = Header(None)):
    """Run one paper-trading decision cycle."""
    get_user(authorization)
    p = get_pipeline()

    def run():
        result = p.run_finance_cycle()
        logger.info(f"Finance cycle: {result.get('decision')}")

    background_tasks.add_task(run)
    return {"status": "started", "message": "Paper trading döngüsü başladı (sanal para)."}


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

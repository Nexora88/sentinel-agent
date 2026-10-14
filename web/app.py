"""
Sentinel Web Interface
Self-hosted control panel + chat. No Telegram required.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Ensure project root is on path
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

from core.pipeline import SentinelPipeline
from core.scheduler import SentinelScheduler
from agents.knowledge_expander import KnowledgeExpander

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentinel.web")

app = FastAPI(title="Sentinel Agent", version="2.0")

# Templates & static
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Shared instances
pipeline: Optional[SentinelPipeline] = None
expander: Optional[KnowledgeExpander] = None
scheduler: Optional[SentinelScheduler] = None
chat_history: List[dict] = []


def get_pipeline() -> SentinelPipeline:
    global pipeline
    if pipeline is None:
        pipeline = SentinelPipeline()
    return pipeline


def get_expander() -> KnowledgeExpander:
    global expander
    if expander is None:
        p = get_pipeline()
        expander = KnowledgeExpander(ollama=p.ollama, memory=p.memory)
    return expander


class ChatRequest(BaseModel):
    message: str


class ExpandRequest(BaseModel):
    topic: Optional[str] = None


class SeedRequest(BaseModel):
    topic: str


@app.on_event("startup")
async def startup():
    logger.info("Sentinel Web UI starting...")
    get_pipeline()
    get_expander()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/status")
async def api_status():
    p = get_pipeline()
    e = get_expander()
    status = p.status()
    universe = e.get_status()
    return {
        "assistant": status,
        "universe": universe,
        "pending_approvals": len(p.permissions.list_pending()),
        "chat_turns": len(chat_history),
    }


@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    p = get_pipeline()
    message = req.message.strip()
    if not message:
        return {"reply": "Boş mesaj."}

    # Special commands from UI
    lower = message.lower()
    if lower in ("/status", "durum", "status"):
        reply = p.status()
    elif lower.startswith("/expand") or lower.startswith("genişlet"):
        e = get_expander()
        result = e.expand_once()
        reply = (
            f"🌌 Bilgi evreni genişledi.\n"
            f"Konu: {result['topic']}\n"
            f"Yeni sayfa: {result['pages_ingested']}\n"
            f"Toplam bilgi: {result['total_knowledge_pages']}"
        )
    else:
        reply = p.chat(message)

    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": reply})
    # Keep last 100 turns in memory
    if len(chat_history) > 200:
        chat_history[:] = chat_history[-200:]

    return {"reply": reply}


@app.get("/api/history")
async def api_history():
    return {"history": chat_history[-40:]}


@app.post("/api/expand")
async def api_expand(req: ExpandRequest, background_tasks: BackgroundTasks):
    e = get_expander()
    if req.topic:
        e.add_seed_topic(req.topic)

    def run_expand():
        result = e.expand_once(extra_topics=[req.topic] if req.topic else None)
        logger.info(f"Background expansion done: {result}")

    background_tasks.add_task(run_expand)
    return {"status": "started", "message": "Bilgi genişletme arka planda başladı."}


@app.post("/api/seed")
async def api_seed(req: SeedRequest):
    e = get_expander()
    e.add_seed_topic(req.topic)
    return {"status": "ok", "message": f"Yeni tohum eklendi: {req.topic}"}


@app.get("/api/universe")
async def api_universe():
    e = get_expander()
    return e.get_status()


@app.get("/api/approvals")
async def api_approvals():
    p = get_pipeline()
    pending = p.permissions.list_pending()
    return {"pending": pending}


@app.post("/api/approvals/{index}/approve")
async def api_approve(index: int):
    p = get_pipeline()
    ok = p.permissions.approve(index)
    return {"success": ok}


@app.post("/api/approvals/{index}/reject")
async def api_reject(index: int):
    p = get_pipeline()
    ok = p.permissions.reject(index)
    return {"success": ok}


@app.post("/api/knowledge/search")
async def api_knowledge_search(req: ChatRequest):
    e = get_expander()
    context = e.search_knowledge(req.message, k=6)
    return {"context": context}


def create_app():
    return app


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("WEB_PORT", "8000"))
    uvicorn.run("web.app:app", host="0.0.0.0", port=port, reload=False)

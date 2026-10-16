"""Ek MKAOS API rotaları — yetenek matrisi, yerel poster, evren büyümesi."""
from __future__ import annotations

from typing import Callable, Optional

from fastapi import Header, HTTPException
from pydantic import BaseModel, Field


class PosterRequest(BaseModel):
    title: str = Field(default="MKAOS", max_length=200)
    body: str = Field(default="", max_length=4000)


class GrowthSeedRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=200)


def register_extra_routes(app, get_user: Callable, get_pipeline: Callable) -> None:
    @app.get("/api/capabilities")
    async def api_capabilities(authorization: Optional[str] = Header(None)):
        get_user(authorization)
        from core.capability_matrix import build_capability_matrix
        from pathlib import Path

        matrix = build_capability_matrix(Path(".").resolve())
        # Universe growth stats if pipeline available
        try:
            p = get_pipeline(get_user(authorization)["username"])
            uni = p.knowledge_expander.get_status() if hasattr(p, "knowledge_expander") else {}
        except Exception:
            uni = {}
        matrix["universe"] = uni
        return matrix

    @app.post("/api/media/poster")
    async def api_media_poster(req: PosterRequest, authorization: Optional[str] = Header(None)):
        get_user(authorization)
        from core.media.local_canvas import LocalCanvas, LocalCanvasError

        try:
            result = LocalCanvas().poster(req.title.strip(), req.body.strip())
        except LocalCanvasError as exc:
            raise HTTPException(503, str(exc)) from exc
        return result

    @app.post("/api/universe/grow")
    async def api_universe_grow(authorization: Optional[str] = Header(None)):
        """Bir tur bilgi genişletme (ALLOW_WEB_RESEARCH gerekir; aksi halde deferred)."""
        user = get_user(authorization)
        p = get_pipeline(user["username"])
        if not hasattr(p, "knowledge_expander"):
            raise HTTPException(503, "Bilgi evreni bileşeni yok")
        return p.knowledge_expander.expand_once()

    @app.post("/api/universe/seed")
    async def api_universe_seed_topic(req: GrowthSeedRequest, authorization: Optional[str] = Header(None)):
        user = get_user(authorization)
        p = get_pipeline(user["username"])
        p.knowledge_expander.add_seed_topic(req.topic.strip())
        return {"ok": True, "topic": req.topic.strip(), "seeds": p.knowledge_expander.get_status().get("seed_count")}

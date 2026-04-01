from __future__ import annotations

import os
import uuid
from pathlib import Path

import httpx
import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .manifest import rewrite_master_playlist, stitch_media_playlist

app = FastAPI(title="MediaTailor MVP", version="0.1.0")

ORIGIN_BASE_URL = os.getenv("ORIGIN_BASE_URL", "http://localhost:8080/live").rstrip("/")
PUBLIC_ORIGIN_BASE_URL = os.getenv("PUBLIC_ORIGIN_BASE_URL", "http://localhost:8080").rstrip("/")
BREAK_CONFIG = Path(os.getenv("BREAK_CONFIG", "/app/config/ad_breaks.yaml"))
ADS_DIR = Path(os.getenv("ADS_DIR", "/srv/origin/ads"))
STATIC_DIR = Path(__file__).resolve().parent / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def load_breaks() -> list[dict]:
    if not BREAK_CONFIG.exists():
        return []
    data = yaml.safe_load(BREAK_CONFIG.read_text(encoding="utf-8")) or {}
    return data.get("breaks", [])


@app.get("/")
async def demo_home() -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/demo")
async def demo_page() -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/session")
async def create_session() -> JSONResponse:
    session_id = str(uuid.uuid4())
    payload = {
        "session_id": session_id,
        "master_url": f"/ssai/master.m3u8?session={session_id}",
        "breaks": load_breaks(),
    }
    return JSONResponse(payload)


@app.get("/ssai/master.m3u8")
async def ssai_master(session: str = Query(..., min_length=4)) -> PlainTextResponse:
    master_url = f"{ORIGIN_BASE_URL}/master.m3u8"
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(master_url)

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"origin master fetch failed: {response.status_code}")

    return PlainTextResponse(
        rewrite_master_playlist(response.text, session),
        media_type="application/vnd.apple.mpegurl",
    )


@app.get("/ssai/media.m3u8")
async def ssai_media(
    session: str = Query(..., min_length=4),
    variant: str = Query(..., min_length=3),
) -> PlainTextResponse:
    _ = session
    variant_url = f"{ORIGIN_BASE_URL}/{variant}"
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(variant_url)

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"origin variant fetch failed: {response.status_code}")

    stitched = stitch_media_playlist(
        response.text,
        variant=variant,
        public_origin_base_url=PUBLIC_ORIGIN_BASE_URL,
        ad_breaks=load_breaks(),
        ads_dir=ADS_DIR,
    )
    return PlainTextResponse(stitched, media_type="application/vnd.apple.mpegurl")

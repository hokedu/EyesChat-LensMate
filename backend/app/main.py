"""EyesChat-LensMate backend entry point."""
import logging
import os
import socket
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .core.config import settings
from .routers import ws

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name, "version": "2.0.0"}


@app.get("/api/config")
async def get_config():
    return {
        "ws_url": f"ws://127.0.0.1:{settings.port}/ws/chat",
        "model": settings.llm_model,
        "max_frames": settings.max_context_frames,
    }


@app.get("/favicon.ico")
async def favicon():
    fav_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "favicon.ico")
    if os.path.isfile(fav_path):
        return FileResponse(fav_path)
    from fastapi.responses import Response
    return Response(status_code=204)


app.include_router(ws.router)

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    logger.info("Frontend mounted from: %s", frontend_dir)
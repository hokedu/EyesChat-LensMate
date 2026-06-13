"""EyesChat-LensMate backend entry point."""
import logging
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
logger.info("Frontend dir: %s (exists=%s)", frontend_dir, os.path.isdir(frontend_dir))

if os.path.isdir(frontend_dir):
    # Serve static assets (JS, CSS, images)
    import stat
    from fastapi.staticfiles import StaticFiles
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


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
    from fastapi.responses import Response
    return Response(status_code=204)


# Register WebSocket router BEFORE catch-all
app.include_router(ws.router)


@app.get("/{path:path}")
async def serve_frontend(path: str):
    """Serve frontend SPA - all non-API routes return index.html."""
    if os.path.isdir(frontend_dir):
        full_path = os.path.join(frontend_dir, path)
        # If file exists and matches a MIME type, serve it
        if os.path.isfile(full_path) and not path.startswith("ws/"):
            return FileResponse(full_path)
        # SPA fallback - return index.html for all routes
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
    return {"detail": "Frontend not found", "path": path}, 404
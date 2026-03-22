"""
VieNeu TTS API — FastAPI Application
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.api.v1 import auth, users, api_keys, tts, refs, sentences, training, admin

# Frontend build directory
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    print(f"🦜 {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    print(f"📁 Storage: {settings.STORAGE_PATH}")
    print(f"🧠 VieNeu mode: {settings.VIENEU_MODE}")
    if FRONTEND_DIR.exists():
        print(f"🌐 Frontend: {FRONTEND_DIR}")
    else:
        print(f"⚠️  Frontend not found at {FRONTEND_DIR}")
    yield
    print("🦜 Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Vietnamese Text-to-Speech Platform powered by VieNeu-TTS",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API Routes ───────────────────────────────────
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(api_keys.router, prefix="/api/v1/api-keys", tags=["API Keys"])
app.include_router(tts.router, prefix="/api/v1/tts", tags=["TTS"])
app.include_router(refs.router, prefix="/api/v1/refs", tags=["References"])
app.include_router(sentences.router, prefix="/api/v1/sentences", tags=["Sentences"])
app.include_router(training.router, prefix="/api/v1/training", tags=["Training"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])


@app.get("/health")
async def health():
    return {"status": "healthy"}


# ─── Frontend Static Files ───────────────────────
if FRONTEND_DIR.exists():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="static")

    # Serve root and SPA catch-all
    @app.get("/")
    async def serve_root():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """Serve frontend SPA — return index.html for all non-API routes."""
        file_path = FRONTEND_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIR / "index.html"))
else:
    @app.get("/")
    async def root():
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running",
            "frontend": "not built — run: cd web/frontend && npm run build",
        }

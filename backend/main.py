from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .auth import seed_admin
from .config import settings
from .database import Base, engine
from .routers import accounts as accounts_router
from .routers import auth as auth_router
from .routers import evidence as evidence_router
from .routers import violations as violations_router
from .ws import manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    for d in ("inbox", "readable", "unreadable", "reports"):
        (Path(settings.STORAGE_ROOT) / d).mkdir(parents=True, exist_ok=True)
    seed_admin()
    yield

app = FastAPI(title="Roadguard API", version="1.1", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router.router)
app.include_router(accounts_router.router)
app.include_router(evidence_router.router)
app.include_router(violations_router.router)

@app.get("/", tags=["health"])
def root():
    return {"service": "Roadguard API", "version": "1.1",
            "docs": "/docs", "health": "/health"}

@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}

@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
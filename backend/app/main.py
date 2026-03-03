from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.conversations import router as conversations_router
from app.api.decisions import router as decisions_router
from app.api.events import router as events_router
from app.api.history import router as history_router
from app.api.memory import router as memory_router
from app.api.queue import router as queue_router
from app.core.config import get_settings
from app.services.event_source import event_simulator

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: nothing automatic (simulator starts via API)
    yield
    # Shutdown: stop simulator if running
    if event_simulator.running:
        await event_simulator.stop()


app = FastAPI(title="SwarmOps", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(conversations_router)
app.include_router(decisions_router)
app.include_router(events_router)
app.include_router(history_router)
app.include_router(memory_router)
app.include_router(queue_router)


@app.get("/health")
async def health():
    return {"status": "ok"}

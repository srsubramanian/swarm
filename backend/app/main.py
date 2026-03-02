from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.conversations import router as conversations_router
from app.api.history import router as history_router
from app.api.queue import router as queue_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="SwarmOps", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(conversations_router)
app.include_router(history_router)
app.include_router(queue_router)


@app.get("/health")
async def health():
    return {"status": "ok"}

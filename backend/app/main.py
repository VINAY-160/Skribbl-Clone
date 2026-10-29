from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import leaderboard, rooms
from app.config import CORS_ORIGINS
from app.dependencies import database
from app.websocket.handlers import ws_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.init_schema()
    yield


app = FastAPI(title="Skribbl Clone API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(rooms.router, prefix="/api")
app.include_router(leaderboard.router, prefix="/api")
app.include_router(ws_router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}

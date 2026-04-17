#!/usr/bin/env python3
"""
FastAPI backend для Telegram WebApp CartingBot
"""
import sys
import os

# api/main.py → api → project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.database.db import init_db
from api.routes import archive, races, stats, leaderboard

app = FastAPI(
    title="CartingBot API",
    description="REST API для Telegram WebApp — результаты картинга",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    init_db()


app.include_router(archive.router, prefix="/api", tags=["archive"])
app.include_router(races.router, prefix="/api", tags=["races"])
app.include_router(stats.router, prefix="/api", tags=["stats"])
app.include_router(leaderboard.router, prefix="/api", tags=["leaderboard"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    from core.config.config import API_HOST, API_PORT
    uvicorn.run("api.main:app", host=API_HOST, port=API_PORT, reload=False)

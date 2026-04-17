#!/usr/bin/env python3
"""
FastAPI backend для Telegram WebApp CartingBot
"""
import sys
import os

# api/main.py → api → project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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


@app.get("/api/photo/{user_id}")
async def get_photo(user_id: int):
    """
    Отдаёт фото профиля пользователя.
    Если нет в кэше — скачивает через Bot API и кэширует.
    """
    import aiohttp
    from core.config.config import DATABASE_PATH, BOT_TOKEN

    photos_dir = Path(DATABASE_PATH).parent / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)
    photo_path = photos_dir / f"{user_id}.jpg"

    if not photo_path.exists() and BOT_TOKEN:
        try:
            async with aiohttp.ClientSession() as session:
                base = f"https://api.telegram.org/bot{BOT_TOKEN}"
                async with session.get(f"{base}/getUserProfilePhotos?user_id={user_id}&limit=1") as r:
                    data = await r.json()
                if data.get("ok") and data["result"]["total_count"] > 0:
                    file_id = data["result"]["photos"][0][-1]["file_id"]
                    async with session.get(f"{base}/getFile?file_id={file_id}") as r:
                        fdata = await r.json()
                    file_path = fdata["result"]["file_path"]
                    async with session.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}") as r:
                        if r.status == 200:
                            photo_path.write_bytes(await r.read())
        except Exception:
            pass

    if not photo_path.exists():
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(photo_path, media_type="image/jpeg")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    from core.config.config import API_HOST, API_PORT
    uvicorn.run("api.main:app", host=API_HOST, port=API_PORT, reload=False)

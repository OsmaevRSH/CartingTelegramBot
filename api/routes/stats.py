import json
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from core.database.db import (
    get_user_competitors, get_competitor_by_key,
    save_competitor, delete_competitor, get_all_users, upsert_user_profile,
)
from core.models.models import LapData

router = APIRouter()


class LapTimeModel(BaseModel):
    lap_number: int
    lap_time: Optional[str] = None
    sector1: Optional[str] = None
    sector2: Optional[str] = None
    sector3: Optional[str] = None
    sector4: Optional[str] = None


class CompetitorModel(BaseModel):
    id: str
    num: str
    name: str
    pos: int
    laps: int
    theor_lap: int
    best_lap: str
    binary_laps: str = ""
    theor_lap_formatted: Optional[str] = None
    display_name: Optional[str] = None
    gap_to_leader: Optional[str] = None
    lap_times: Optional[List[LapTimeModel]] = None


class SaveStatsRequest(BaseModel):
    user_id: int
    date: str
    race_number: str
    race_href: str
    competitor: CompetitorModel


def _row_to_dict(row: tuple) -> dict:
    """Преобразует кортеж из БД в словарь."""
    keys = [
        "date", "race_number", "race_href", "competitor_id", "num", "name",
        "pos", "laps", "theor_lap", "best_lap", "binary_laps",
        "theor_lap_formatted", "display_name", "gap_to_leader", "lap_times_json",
    ]
    return dict(zip(keys, row))


@router.get("/users")
async def get_users():
    """Возвращает всех пользователей с сохранёнными заездами."""
    return get_all_users()


class RegisterUserRequest(BaseModel):
    user_id: int
    name: str
    username: Optional[str] = None
    photo_url: Optional[str] = None


@router.post("/users/me")
async def register_user(body: RegisterUserRequest):
    """Сохраняет Telegram-имя, username и аватар пользователя."""
    upsert_user_profile(body.user_id, body.name, body.username, body.photo_url)
    return {"ok": True}


@router.get("/stats/{user_id}")
async def get_user_stats(user_id: int):
    """Возвращает все заезды пользователя."""
    rows = get_user_competitors(user_id)
    return [_row_to_dict(r) for r in rows]


@router.post("/stats")
async def save_stats(body: SaveStatsRequest):
    """Сохраняет результат заезда пользователя."""
    competitor_data = body.competitor.model_dump()

    if competitor_data.get("lap_times"):
        lap_objects = [
            LapData(
                lap_number=lt["lap_number"],
                lap_time=lt.get("lap_time") or "",
                sector1=lt.get("sector1"),
                sector2=lt.get("sector2"),
                sector3=lt.get("sector3"),
                sector4=lt.get("sector4"),
            )
            for lt in competitor_data["lap_times"]
        ]
        competitor_data["lap_times"] = lap_objects

    saved = save_competitor(
        user_id=body.user_id,
        date=body.date,
        race_number=body.race_number,
        race_href=body.race_href,
        competitor_data=competitor_data,
    )
    return {"saved": saved}


@router.delete("/stats/{user_id}/{date}/{race_number}/{num}")
async def delete_stats(user_id: int, date: str, race_number: str, num: str):
    """Удаляет запись заезда пользователя."""
    deleted = delete_competitor(user_id, date, race_number, num)
    if not deleted:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return {"deleted": True}

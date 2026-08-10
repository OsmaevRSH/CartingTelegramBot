import json
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from core.database.db import (
    get_user_competitors, get_competitor_by_key,
    save_competitor, delete_competitor, get_all_users, upsert_user_profile,
)
from core.models.models import LapData
from api.dependencies import require_mobile_user

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


class MobileSaveStatsRequest(BaseModel):
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


def _competitor_data(competitor: CompetitorModel) -> dict:
    competitor_data = competitor.model_dump()
    if competitor_data.get("lap_times"):
        competitor_data["lap_times"] = [
            LapData(
                lap_number=lap_time["lap_number"],
                lap_time=lap_time.get("lap_time") or "",
                sector1=lap_time.get("sector1"),
                sector2=lap_time.get("sector2"),
                sector3=lap_time.get("sector3"),
                sector4=lap_time.get("sector4"),
            )
            for lap_time in competitor_data["lap_times"]
        ]
    return competitor_data


def _mobile_user(authorization: Optional[str] = Header(default=None)) -> int:
    if not authorization:
        return require_mobile_user(None)
    scheme, separator, token = authorization.partition(" ")
    credentials = (
        HTTPAuthorizationCredentials(scheme=scheme, credentials=token)
        if separator and token
        else None
    )
    return require_mobile_user(credentials)


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
    saved = save_competitor(
        user_id=body.user_id,
        date=body.date,
        race_number=body.race_number,
        race_href=body.race_href,
        competitor_data=_competitor_data(body.competitor),
    )
    return {"saved": saved}


@router.delete("/stats/{user_id}/{date}/{race_number}/{num}")
async def delete_stats(user_id: int, date: str, race_number: str, num: str):
    """Удаляет запись заезда пользователя."""
    deleted = delete_competitor(user_id, date, race_number, num)
    if not deleted:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return {"deleted": True}


@router.get("/mobile/stats")
async def get_mobile_stats(user_id: int = Depends(_mobile_user)):
    return [_row_to_dict(row) for row in get_user_competitors(user_id)]


@router.post("/mobile/stats")
async def save_mobile_stats(
    body: MobileSaveStatsRequest,
    user_id: int = Depends(_mobile_user),
):
    saved = save_competitor(
        user_id=user_id,
        date=body.date,
        race_number=body.race_number,
        race_href=body.race_href,
        competitor_data=_competitor_data(body.competitor),
    )
    return {"saved": saved}


@router.delete("/mobile/stats/{date}/{race_number}/{num}")
async def delete_mobile_stats(
    date: str,
    race_number: str,
    num: str,
    user_id: int = Depends(_mobile_user),
):
    deleted = delete_competitor(user_id, date, race_number, num)
    if not deleted:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return {"deleted": True}

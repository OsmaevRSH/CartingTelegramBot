from fastapi import APIRouter, Query
from datetime import date as date_module
from core.database.db import get_best_competitors, get_best_competitors_today, get_best_karts_today

router = APIRouter()


def _row_to_dict(row: tuple) -> dict:
    keys = [
        "user_id", "date", "race_number", "num", "name", "display_name",
        "theor_lap", "theor_lap_formatted", "best_lap", "pos",
        "telegram_name", "photo_url",
    ]
    return dict(zip(keys, row))


@router.get("/leaderboard")
async def get_leaderboard(limit: int = 20):
    """Топ гонщиков всех времён по лучшему кругу."""
    rows = get_best_competitors(limit)
    return [_row_to_dict(r) for r in rows]


@router.get("/leaderboard/today")
async def get_leaderboard_today(
    date: str = Query(default=None, description="Дата в формате DD.MM.YYYY"),
    limit: int = 20,
):
    """Топ гонщиков за конкретный день."""
    if not date:
        date = date_module.today().strftime("%d.%m.%Y")
    rows = get_best_competitors_today(date, limit)
    return [_row_to_dict(r) for r in rows]


@router.get("/karts/today")
async def get_karts_today(
    date: str = Query(default=None, description="Дата в формате DD.MM.YYYY"),
):
    """Рейтинг картов за день — лучший круг каждого карта."""
    if not date:
        date = date_module.today().strftime("%d.%m.%Y")
    rows = get_best_karts_today(date)
    return [
        {
            "num": r[0],
            "best_lap": r[1],
            "best_lap_ms": r[2],
            "drivers": r[3],
            "best_driver": r[4],
            "best_driver_photo": r[5],
        }
        for r in rows
    ]

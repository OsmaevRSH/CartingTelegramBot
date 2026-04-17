from fastapi import APIRouter, Query
from datetime import date as date_module
from core.database.db import get_best_competitors, get_best_competitors_today

router = APIRouter()


def _row_to_dict(row: tuple) -> dict:
    keys = [
        "user_id", "date", "race_number", "num", "name", "display_name",
        "theor_lap", "theor_lap_formatted", "best_lap", "pos", "telegram_name",
    ]
    return dict(zip(keys, row))


@router.get("/leaderboard")
async def get_leaderboard(limit: int = 20):
    """Топ гонщиков всех времён по лучшему кругу."""
    rows = get_best_competitors(limit)
    return [_row_to_dict(r) for r in rows]


@router.get("/leaderboard/today")
async def get_leaderboard_today(
    date: str = Query(
        default=None,
        description="Дата в формате DD.MM.YYYY (по умолчанию сегодня)",
    ),
    limit: int = 20,
):
    """Топ гонщиков за конкретный день."""
    if not date:
        date = date_module.today().strftime("%d.%m.%Y")
    rows = get_best_competitors_today(date, limit)
    return [_row_to_dict(r) for r in rows]

import asyncio
from fastapi import APIRouter, Query, HTTPException
from datetime import date as date_module
from core.database.db import get_best_competitors, get_best_competitors_today
from core.parsers.parsers import ArchiveParser, RaceParser
from core.models.models import ParsingError

router = APIRouter()

_archive_parser = ArchiveParser()
_race_parser = RaceParser()


def _row_to_dict(row: tuple) -> dict:
    keys = [
        "user_id", "date", "race_number", "num", "name", "display_name",
        "theor_lap", "theor_lap_formatted", "best_lap", "pos",
        "telegram_name", "photo_url",
    ]
    return dict(zip(keys, row))


def _time_to_ms(t: str) -> int:
    if not t or t.strip() in ('-', ''):
        return 999_999_999
    try:
        t = t.strip()
        if ':' in t and '.' in t:
            m, rest = t.split(':', 1)
            s, ms = rest.split('.', 1)
            return int(m) * 60_000 + int(s) * 1_000 + int(ms)
    except Exception:
        pass
    return 999_999_999


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
    """
    Рейтинг картов за день — парсит ВСЕ заезды с kartchrono за указанную дату
    и возвращает лучший круг каждого карта среди всех заездов.
    """
    if not date:
        date = date_module.today().strftime("%d.%m.%Y")

    # 1. Получаем список заездов за день
    try:
        day_races_list = await _archive_parser.parse()
    except ParsingError as e:
        raise HTTPException(status_code=502, detail=f"Ошибка архива: {e}")

    today_dr = next(
        (dr for dr in day_races_list if dr.date.strftime("%d.%m.%Y") == date),
        None,
    )
    if not today_dr or not today_dr.races:
        return []

    # 2. Параллельно загружаем результаты всех заездов
    async def fetch_race(race):
        try:
            return await _race_parser.parse(race.href)
        except Exception:
            return []

    all_carts_lists = await asyncio.gather(*[fetch_race(r) for r in today_dr.races])

    # 3. Агрегируем: лучший круг + кол-во заездов на каждом карте
    best_per_kart: dict = {}
    races_count: dict = {}

    for carts in all_carts_lists:
        for cart in carts:
            num = cart.number
            if not num:
                continue
            races_count[num] = races_count.get(num, 0) + 1
            ms = _time_to_ms(cart.best_lap)
            if ms >= 999_999_999:
                continue
            if num not in best_per_kart or ms < best_per_kart[num]['ms']:
                best_per_kart[num] = {
                    'num': num,
                    'best_lap': cart.best_lap,
                    'ms': ms,
                }

    # 4. Сортируем по лучшему времени
    sorted_karts = sorted(best_per_kart.values(), key=lambda x: x['ms'])

    return [
        {
            'num': k['num'],
            'best_lap': k['best_lap'],
            'races': races_count.get(k['num'], 0),
        }
        for k in sorted_karts
    ]

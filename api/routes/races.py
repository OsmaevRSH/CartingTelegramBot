from fastapi import APIRouter, HTTPException, Query
from core.parsers.parsers import RaceParser, FullRaceInfoParser
from core.models.models import ParsingError

router = APIRouter()
_race_parser = RaceParser()
_full_parser = FullRaceInfoParser()


@router.get("/races")
async def get_race_carts(href: str = Query(..., description="Ссылка на заезд")):
    """Возвращает список картов для заезда."""
    try:
        carts, _ = await _race_parser.parse_with_html(href)
        return [
            {"id": c.id, "number": c.number, "best_lap": c.best_lap, "position": c.position}
            for c in carts
        ]
    except ParsingError as e:
        raise HTTPException(status_code=502, detail=f"Ошибка парсинга: {e}")


@router.get("/races/full")
async def get_race_full(href: str = Query(..., description="Ссылка на заезд")):
    """Возвращает полную информацию о заезде с данными по кругам."""
    try:
        carts, html = await _race_parser.parse_with_html(href)
        competitors = await _full_parser.parse(href, race_carts=carts, html=html)
        return [
            {
                "id": c.id,
                "num": c.num,
                "name": c.name,
                "pos": c.pos,
                "laps": c.laps,
                "theor_lap": c.theor_lap,
                "best_lap": c.best_lap,
                "theor_lap_formatted": c.theor_lap_formatted,
                "display_name": c.display_name,
                "gap_to_leader": c.gap_to_leader,
                "lap_times": [
                    {
                        "lap_number": lt.lap_number,
                        "lap_time": lt.lap_time,
                        "sector1": lt.sector1,
                        "sector2": lt.sector2,
                        "sector3": lt.sector3,
                        "sector4": lt.sector4,
                    }
                    for lt in (c.lap_times or [])
                ],
            }
            for c in competitors
        ]
    except ParsingError as e:
        raise HTTPException(status_code=502, detail=f"Ошибка парсинга: {e}")

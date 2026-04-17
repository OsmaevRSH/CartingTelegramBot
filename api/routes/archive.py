from fastapi import APIRouter, HTTPException
from core.parsers.parsers import ArchiveParser
from core.models.models import ParsingError

router = APIRouter()
_parser = ArchiveParser()


@router.get("/archive")
async def get_archive():
    """Возвращает список дней с заездами из архива kartchrono."""
    try:
        day_races = await _parser.parse()
        return [
            {
                "date": dr.date.strftime("%d.%m.%Y"),
                "races": [{"number": r.number, "href": r.href} for r in dr.races],
            }
            for dr in day_races
        ]
    except ParsingError as e:
        raise HTTPException(status_code=502, detail=f"Ошибка парсинга: {e}")

from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class Race:
    number: str
    href: str


@dataclass
class DayRaces:
    date: datetime
    races: List[Race]


@dataclass
class Cart:
    id: str
    number: str
    best_lap: str
    position: str


class ParsingError(Exception):
    """Ошибки парсинга"""
    pass 
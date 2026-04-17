from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

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

@dataclass
class LapData:
    """Данные об одном круге"""
    lap_number: int
    lap_time: str
    sector1: Optional[str] = None
    sector2: Optional[str] = None
    sector3: Optional[str] = None
    sector4: Optional[str] = None

@dataclass
class Competitor:
    """Модель для детальной информации о конкуренте из jsCompetitors"""
    id: str
    num: str
    name: str
    pos: int
    laps: int
    theor_lap: int
    best_lap: str
    binary_laps: str

    theor_lap_formatted: Optional[str] = None
    display_name: Optional[str] = None
    gap_to_leader: Optional[str] = None
    lap_times: Optional[List[LapData]] = None

class ParsingError(Exception):
    """Ошибки парсинга"""
    pass

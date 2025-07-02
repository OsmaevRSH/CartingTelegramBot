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
    lap_number: int                   # Номер круга (0 - стартовый)
    lap_time: str                     # Время круга в формате MM:SS.sss
    sector1: Optional[str] = None     # Сектор 1 (None для стартового круга)
    sector2: Optional[str] = None     # Сектор 2
    sector3: Optional[str] = None     # Сектор 3  
    sector4: Optional[str] = None     # Сектор 4

@dataclass
class Competitor:
    """Модель для детальной информации о конкуренте из jsCompetitors"""
    id: str                          # ID конкурента (ключ в jsCompetitors, например "-10001")
    num: str                         # Номер карта (поле "num")
    name: str                        # Имя пилота (поле "name", может быть пустым)
    pos: int                         # Позиция в заезде (поле "pos")
    laps: int                        # Количество кругов (поле "laps")
    theor_lap: int                   # Теоретический круг в миллисекундах (поле "theor_lap")
    best_lap: str                    # Лучший реальный круг из RaceParser
    binary_laps: str                 # Бинарные данные кругов (поле "binary_laps")
    
    # Вычисляемые поля для удобства
    theor_lap_formatted: Optional[str] = None     # Теоретический круг в формате MM:SS.sss
    display_name: Optional[str] = None            # Отображаемое имя (имя или "Карт #XX")
    gap_to_leader: Optional[str] = None           # Отставание от лидера по теоретическому кругу
    lap_times: Optional[List[LapData]] = None     # Расшифрованные данные кругов

class ParsingError(Exception):
    """Ошибки парсинга"""
    pass 
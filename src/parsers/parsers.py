import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Optional
from src.models.models import Race, DayRaces, Cart, ParsingError, Competitor, LapData
import json
import re
import base64
import struct


class ArchiveParser:
    """Парсер архива заездов"""

    def __init__(self):
        self.url_string = "https://mayak.kartchrono.com/archive/"

    async def parse(self) -> List[DayRaces]:
        """Парсит главную страницу архива"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url_string) as response:
                    response.raise_for_status()
                    html = await response.text()

            return self._parse_html(html)
        except aiohttp.ClientError as e:
            raise ParsingError(f"Ошибка загрузки страницы: {e}")
        except Exception as e:
            raise ParsingError(f"Ошибка парсинга: {e}")

    def _parse_html(self, html: str) -> List[DayRaces]:
        """Парсит HTML и извлекает данные о заездах"""
        soup = BeautifulSoup(html, 'html.parser')
        day_races = []

        # Ищем элементы с классом archiveData
        archive_data = soup.find(class_="archiveData")
        if not archive_data:
            raise ParsingError("Не найден элемент archiveData")

        race_date = None
        races = []

        for element in archive_data.children:
            if hasattr(element, 'get') and element.get('class'):
                # Заголовок с датой
                if 'archiveDateHeader' in element.get('class', []):
                    if race_date:
                        day_races.append(DayRaces(date=race_date, races=races))
                        races = []

                    date_text = element.get_text().strip()
                    try:
                        race_date = datetime.strptime(date_text, "%d.%m.%Y")
                    except ValueError:
                        print(f"Не удалось распарсить дату: {date_text}")
                        continue

                # Строка с данными заезда
                elif 'archiveDataRow' in element.get('class', []):
                    link_element = element.find('a')
                    if link_element:
                        href = link_element.get('href', '')
                        # Ищем номер заезда в структуре ссылки
                        race_number_element = link_element.find()
                        if race_number_element:
                            race_number_element = race_number_element.find()
                            if race_number_element:
                                race_number = race_number_element.get_text().strip()
                            else:
                                race_number = link_element.get_text().strip()
                        else:
                            race_number = link_element.get_text().strip()

                        races.append(Race(number=race_number, href=href))

        # Добавляем последнюю дату, если есть
        if race_date and races:
            day_races.append(DayRaces(date=race_date, races=races))

        return day_races


class RaceParser:
    """Парсер результатов конкретного заезда"""

    def __init__(self):
        self.url_string = "https://mayak.kartchrono.com/archive/"

    async def parse(self, href: str) -> List[Cart]:
        """Парсит результаты конкретного заезда"""
        try:
            url = self.url_string + href
            print(f"🔗 Парсим URL: {url}")

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    html = await response.text()

            return self._parse_html(html)
        except aiohttp.ClientError as e:
            raise ParsingError(f"Ошибка загрузки страницы: {e}")
        except Exception as e:
            raise ParsingError(f"Ошибка парсинга: {e}")

    def _parse_html(self, html: str) -> List[Cart]:
        """Парсит HTML и извлекает результаты заезда"""
        soup = BeautifulSoup(html, 'html.parser')
        race_carts = []

        # Ищем таблицу с результатами
        results_table = soup.find(id="resultsTable")
        if not results_table:
            raise ParsingError("Не найдена таблица с результатами")

        # Ищем строки с данными
        data_rows = results_table.find_all(class_="dataRow")

        for row in data_rows:
            # Извлекаем данные из каждой строки
            number_element = row.find(id="num")
            best_lap_element = row.find(id="best_lap_time")
            position_element = row.find(id="pos")

            number = number_element.get_text().strip() if number_element else ""
            best_lap = best_lap_element.get_text().strip() if best_lap_element else ""
            position = position_element.get_text().strip() if position_element else ""

            race_carts.append(Cart(
                id="",  # competitorid не используется в Swift коде
                number=number,
                best_lap=best_lap,
                position=position
            ))

        return race_carts


class FullRaceInfoParser:
    """Парсер полной информации по заезду с информацией о секторах"""

    def __init__(self):
        self.url_string = "https://mayak.kartchrono.com/archive/"

    async def parse(self, href: str, race_carts: List = None) -> List[Competitor]:
        """Парсит полную информацию о конкурентах заезда"""
        try:
            url = self.url_string + href
            print(f"🔗 Парсим полную информацию по URL: {url}")

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    html = await response.text()

            return self._parse_html(html, race_carts)
        except aiohttp.ClientError as e:
            raise ParsingError(f"Ошибка загрузки страницы: {e}")
        except Exception as e:
            raise ParsingError(f"Ошибка парсинга: {e}")

    def _parse_html(self, html: str, race_carts: List = None) -> List[Competitor]:
        """Парсит HTML и извлекает данные о конкурентах из jsCompetitors"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Ищем переменную jsCompetitors в скриптах
        js_competitors_data = self._extract_js_competitors(html)
        if not js_competitors_data:
            raise ParsingError("Не найдена переменная jsCompetitors")

        # Парсим JSON данные
        try:
            competitors_json = json.loads(js_competitors_data)
            return self._parse_competitors_json(competitors_json, race_carts)
        except json.JSONDecodeError as e:
            raise ParsingError(f"Ошибка парсинга JSON: {e}")

    def _extract_js_competitors(self, html: str) -> Optional[str]:
        """Извлекает данные из переменной jsCompetitors"""
        # Ищем паттерн var jsCompetitors = {...}
        pattern = r'var\s+jsCompetitors\s*=\s*(\{.*?\});'
        match = re.search(pattern, html, re.DOTALL)
        
        if match:
            return match.group(1)
        
        # Альтернативный поиск без var
        pattern = r'jsCompetitors\s*=\s*(\{.*?\});'
        match = re.search(pattern, html, re.DOTALL)
        
        if match:
            return match.group(1)
            
        return None

    def _parse_competitors_json(self, competitors_json: dict, race_carts: List = None) -> List[Competitor]:
        """Парсит JSON данные конкурентов в объекты Competitor"""
        competitors = []
        
        # Создаем словарь для быстрого поиска лучших кругов по номеру карта
        best_laps_dict = {}
        if race_carts:
            for cart in race_carts:
                best_laps_dict[cart.number] = cart.best_lap
        
        for competitor_id, competitor_data in competitors_json.items():
            # Извлекаем данные напрямую из JSON
            num = str(competitor_data.get('num', ''))
            name = str(competitor_data.get('name', ''))
            pos = int(competitor_data.get('pos', 0))
            laps = int(competitor_data.get('laps', 0))
            theor_lap = int(competitor_data.get('theor_lap', 0))
            binary_laps = str(competitor_data.get('binary_laps', ''))
            
            # Получаем лучший круг из RaceParser
            best_lap = best_laps_dict.get(num, "")
            
            # Вычисляем форматированные поля
            theor_lap_formatted = self._format_time(theor_lap)
            display_name = name if name.strip() else f"Карт #{num}"
            
            # Расшифровываем binary_laps для получения данных о кругах
            lap_times = self._decode_binary_laps(binary_laps)
            
            competitor = Competitor(
                id=competitor_id,
                num=num,
                name=name,
                pos=pos,
                laps=laps,
                theor_lap=theor_lap,
                best_lap=best_lap,
                binary_laps=binary_laps,
                theor_lap_formatted=theor_lap_formatted,
                display_name=display_name,
                gap_to_leader=None,  # Вычислим после создания всех объектов
                lap_times=lap_times  # Добавляем расшифрованные данные кругов
            )
            
            competitors.append(competitor)
        
        # Сортируем по позиции
        competitors.sort(key=lambda x: x.pos)
        
        # Вычисляем gap_to_leader по теоретическим кругам
        if competitors:
            leader_theor_lap = competitors[0].theor_lap
            for competitor in competitors:
                if competitor.pos == 1:
                    competitor.gap_to_leader = "Лидер"
                else:
                    gap_ms = competitor.theor_lap - leader_theor_lap
                    competitor.gap_to_leader = f"+{self._format_time(gap_ms)}"
        
        return competitors

    def _format_time(self, time_ms: int) -> str:
        """Преобразует время из миллисекунд в формат MM:SS.sss"""
        if time_ms <= 0:
            return "00:00.000"
            
        minutes = time_ms // 60000
        seconds = (time_ms % 60000) // 1000
        milliseconds = time_ms % 1000
        return f"{minutes}:{seconds:02d}.{milliseconds:03d}"

    def _decode_binary_laps(self, binary_laps: str) -> List[LapData]:
        """Расшифровывает binary_laps и возвращает данные о кругах"""
        if not binary_laps:
            return []
        
        try:
            # Декодируем base64
            binary_data = base64.b64decode(binary_laps)
            lap_times = []
            
            # Читаем данные блоками по 52 байта (как в оригинальном JS коде)
            offset = 0
            data_length = len(binary_data)
            
            while offset < data_length:
                # Проверяем, хватает ли данных для полного блока
                if offset + 52 > data_length:
                    break
                
                try:
                    # Читаем структуру блока (52 байта)
                    competitor_id = struct.unpack('<i', binary_data[offset:offset+4])[0]
                    lap_id = struct.unpack('<i', binary_data[offset+4:offset+8])[0]
                    lap_num = struct.unpack('<i', binary_data[offset+8:offset+12])[0]
                    race_lap_num = struct.unpack('<i', binary_data[offset+12:offset+16])[0]
                    lap_pos = struct.unpack('<i', binary_data[offset+16:offset+20])[0]
                    
                    # Сектора
                    sector1 = struct.unpack('<i', binary_data[offset+20:offset+24])[0]
                    sector2 = struct.unpack('<i', binary_data[offset+24:offset+28])[0]
                    sector3 = struct.unpack('<i', binary_data[offset+28:offset+32])[0]
                    
                    # Время круга
                    lap_time = struct.unpack('<i', binary_data[offset+32:offset+36])[0]
                    
                    # Timestamp (8 байт)
                    timestamp_low = struct.unpack('<I', binary_data[offset+36:offset+40])[0]
                    timestamp_high = struct.unpack('<I', binary_data[offset+40:offset+44])[0]
                    
                    # Флаги
                    lap_flags = struct.unpack('<i', binary_data[offset+44:offset+48])[0]
                    
                    # Четвертый сектор
                    sector4 = struct.unpack('<i', binary_data[offset+48:offset+52])[0]
                    
                    # Создаем объект LapData
                    if lap_num == 0:
                        # Стартовый круг
                        lap_data = LapData(
                            lap_number=0,
                            lap_time="",
                            sector1=None,
                            sector2=self._format_time(sector2) if sector2 > 0 else None,
                            sector3=self._format_time(sector3) if sector3 > 0 else None,
                            sector4=self._format_time(sector4) if sector4 > 0 else None
                        )
                    else:
                        # Обычный круг - используем lap_time из данных, если он разумный
                        if lap_time > 0 and lap_time < 600000:  # Разумное время круга (до 10 минут)
                            final_lap_time = lap_time
                        else:
                            # Если lap_time неразумный, вычисляем как сумму секторов
                            final_lap_time = sector1 + sector2 + sector3 + sector4
                        
                        lap_data = LapData(
                            lap_number=lap_num,
                            lap_time=self._format_time(final_lap_time) if final_lap_time > 0 else None,
                            sector1=self._format_time(sector1) if sector1 > 0 else None,
                            sector2=self._format_time(sector2) if sector2 > 0 else None,
                            sector3=self._format_time(sector3) if sector3 > 0 else None,
                            sector4=self._format_time(sector4) if sector4 > 0 else None
                        )
                    
                    lap_times.append(lap_data)
                    
                except struct.error:
                    pass
                
                offset += 52
            
            # Сортируем по номеру круга
            lap_times.sort(key=lambda x: x.lap_number)
            
            return lap_times
            
        except Exception as e:
            print(f"Ошибка расшифровки binary_laps: {e}")
            return []
    
    def _calculate_sector1(self, lap_time_ms: int, sector2_ms: int, sector3_ms: int, sector4_ms: int) -> Optional[str]:
        """Вычисляет время первого сектора как остаток от общего времени круга"""
        try:
            if sector2_ms > 0 and sector3_ms > 0 and sector4_ms > 0:
                sector1_ms = lap_time_ms - sector2_ms - sector3_ms - sector4_ms
                if 1000 <= sector1_ms <= 120000:  # Разумные границы для сектора
                    return self._format_time(sector1_ms)
        except:
            pass
        return None

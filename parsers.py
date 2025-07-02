import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List
from models import Race, DayRaces, Cart, ParsingError


class ArchiveParser:
    """Парсер архива заездов"""
    
    def __init__(self):
        self.url_string = "https://mayak.kartchrono.com/archive/"
    
    def parse(self) -> List[DayRaces]:
        """Парсит главную страницу архива"""
        try:
            response = requests.get(self.url_string)
            response.raise_for_status()
            
            return self._parse_html(response.text)
        except requests.RequestException as e:
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
    
    def parse(self, href: str) -> List[Cart]:
        """Парсит результаты конкретного заезда"""
        try:
            url = self.url_string + href
            print(f"🔗 Парсим URL: {url}")
            
            response = requests.get(url)
            response.raise_for_status()
            
            return self._parse_html(response.text)
        except requests.RequestException as e:
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
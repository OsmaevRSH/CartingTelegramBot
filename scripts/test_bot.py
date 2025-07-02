#!/usr/bin/env python3
"""
Скрипт для тестирования функций бота
"""
import sys
import os
import asyncio

# Добавляем корневую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parsers.parsers import ArchiveParser
from src.database.db import init_db, get_all_competitors
from src.models.models import ParsingError

async def test_parser():
    """Тестирует парсер архива"""
    print("🧪 Тестирую парсер архива...")
    
    try:
        parser = ArchiveParser()
        day_races = await parser.parse()
        
        print(f"✅ Парсер работает! Найдено {len(day_races)} дней с заездами")
        
        for day_race in day_races[:3]:  # Показываем первые 3 дня
            print(f"📅 {day_race.date.strftime('%d.%m.%Y')} - {len(day_race.races)} заездов")
            for race in day_race.races[:2]:  # Показываем первые 2 заезда
                print(f"   🏁 {race.number} ({race.href})")
            
    except ParsingError as e:
        print(f"❌ Ошибка парсинга: {e}")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")

def test_database():
    """Тестирует базу данных"""
    print("\n🧪 Тестирую базу данных...")
    
    try:
        init_db()
        print("✅ База данных инициализирована")
        
        competitors = get_all_competitors()
        print(f"📊 В базе данных {len(competitors)} записей")
        
    except Exception as e:
        print(f"❌ Ошибка базы данных: {e}")

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов CartingBot...")
    
    # Тест парсера
    await test_parser()
    
    # Тест базы данных
    test_database()
    
    print("\n✅ Тесты завершены!")

if __name__ == "__main__":
    asyncio.run(main()) 
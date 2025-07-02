#!/usr/bin/env python3
"""
Скрипт для проверки здоровья бота
"""
import sys
import os
import asyncio
import aiohttp
from datetime import datetime, timedelta

# Добавляем корневую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import get_all_competitors
from src.parsers.parsers import ArchiveParser
from src.models.models import ParsingError

async def check_website():
    """Проверяет доступность сайта kartchrono.com"""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get("https://mayak.kartchrono.com/archive/") as response:
                if response.status == 200:
                    return True, "Сайт доступен"
                else:
                    return False, f"Сайт недоступен (HTTP {response.status})"
    except aiohttp.ClientError as e:
        return False, f"Ошибка соединения: {e}"
    except Exception as e:
        return False, f"Неожиданная ошибка: {e}"

async def check_parser():
    """Проверяет работу парсера"""
    try:
        parser = ArchiveParser()
        day_races = await parser.parse()
        if day_races:
            return True, f"Парсер работает ({len(day_races)} дней)"
        else:
            return False, "Парсер не вернул данных"
    except ParsingError as e:
        return False, f"Ошибка парсинга: {e}"
    except Exception as e:
        return False, f"Неожиданная ошибка: {e}"

def check_database():
    """Проверяет работу базы данных"""
    try:
        competitors = get_all_competitors()
        return True, f"База данных работает ({len(competitors)} записей)"
    except Exception as e:
        return False, f"Ошибка базы данных: {e}"

def check_log_file():
    """Проверяет наличие и актуальность лог файла"""
    try:
        log_file = "logs/bot.log"
        if os.path.exists(log_file):
            stat = os.stat(log_file)
            modified_time = datetime.fromtimestamp(stat.st_mtime)
            now = datetime.now()
            
            if now - modified_time < timedelta(hours=1):
                return True, "Лог файл актуален"
            else:
                return False, "Лог файл устарел"
        else:
            return False, "Лог файл не найден"
    except Exception as e:
        return False, f"Ошибка проверки лог файла: {e}"

async def main():
    """Основная функция проверки здоровья"""
    print("🏥 Проверка здоровья CartingBot...")
    print("=" * 50)
    
    all_ok = True
    
    # Проверка сайта
    print("🌐 Проверка доступности сайта...")
    site_ok, site_msg = await check_website()
    print(f"   {'✅' if site_ok else '❌'} {site_msg}")
    all_ok = all_ok and site_ok
    
    # Проверка парсера
    print("\n🔍 Проверка парсера...")
    parser_ok, parser_msg = await check_parser()
    print(f"   {'✅' if parser_ok else '❌'} {parser_msg}")
    all_ok = all_ok and parser_ok
    
    # Проверка базы данных
    print("\n🗄️ Проверка базы данных...")
    db_ok, db_msg = check_database()
    print(f"   {'✅' if db_ok else '❌'} {db_msg}")
    all_ok = all_ok and db_ok
    
    # Проверка лог файла
    print("\n📝 Проверка лог файла...")
    log_ok, log_msg = check_log_file()
    print(f"   {'✅' if log_ok else '❌'} {log_msg}")
    all_ok = all_ok and log_ok
    
    print("\n" + "=" * 50)
    if all_ok:
        print("✅ Все проверки пройдены успешно!")
        sys.exit(0)
    else:
        print("❌ Обнаружены проблемы!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 
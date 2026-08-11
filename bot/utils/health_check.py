#!/usr/bin/env python3
"""
Скрипт для проверки здоровья бота
"""
import os
import asyncio
import aiohttp
import sys

# bot/utils/health_check.py → bot/utils → bot → project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database.db import get_all_competitors
from core.parsers.parsers import ArchiveParser
from core.models.models import ParsingError

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


def check_bot_process(proc_root="/proc"):
    """Проверяет, что PID 1 контейнера — основной процесс бота."""
    try:
        cmdline_path = os.path.join(proc_root, "1", "cmdline")
        with open(cmdline_path, "rb") as cmdline_file:
            command = cmdline_file.read().decode(errors="replace")
    except Exception as e:
        return False, f"Ошибка проверки процесса бота: {e}"

    if "bot/main.py" in command:
        return True, "Процесс бота запущен"
    return False, "PID 1 не является процессом бота"


async def main():
    """Основная функция проверки здоровья"""
    print("🏥 Проверка здоровья CartingBot...")
    print("=" * 50)

    all_ok = True

    print("🌐 Проверка доступности сайта...")
    site_ok, site_msg = await check_website()
    print(f"   {'✅' if site_ok else '❌'} {site_msg}")
    all_ok = all_ok and site_ok

    print("\n🔍 Проверка парсера...")
    parser_ok, parser_msg = await check_parser()
    print(f"   {'✅' if parser_ok else '❌'} {parser_msg}")
    all_ok = all_ok and parser_ok

    print("\n🗄️ Проверка базы данных...")
    db_ok, db_msg = check_database()
    print(f"   {'✅' if db_ok else '❌'} {db_msg}")
    all_ok = all_ok and db_ok

    print("\n🤖 Проверка процесса бота...")
    bot_ok, bot_msg = check_bot_process()
    print(f"   {'✅' if bot_ok else '❌'} {bot_msg}")
    all_ok = all_ok and bot_ok

    print("\n" + "=" * 50)
    if all_ok:
        print("✅ Все проверки пройдены успешно!")
        sys.exit(0)
    else:
        print("❌ Обнаружены проблемы!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

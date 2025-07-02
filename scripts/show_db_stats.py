#!/usr/bin/env python3
"""
Скрипт для просмотра статистики базы данных бота
"""

import sys
import os
from pathlib import Path
from collections import defaultdict

# Добавляем корневую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import DB_FILE, get_all_competitors


def main():
    """Показать статистику базы данных"""
    print("📊 Статистика базы данных бота")
    print("=" * 35)
    
    # Проверяем, существует ли файл БД
    if not DB_FILE.exists():
        print("❌ Файл базы данных не найден:", DB_FILE)
        print("💡 Возможно, база данных ещё не создана")
        return
    
    print(f"📁 Файл базы данных: {DB_FILE}")
    print(f"📦 Размер файла: {DB_FILE.stat().st_size / 1024:.1f} KB")
    print()
    
    try:
        # Получаем все данные
        all_competitors = get_all_competitors()
        
        if not all_competitors:
            print("✅ База данных пуста")
            return
        
        # Подсчитываем статистику
        total_races = len(all_competitors)
        unique_users = len(set(comp[0] for comp in all_competitors))
        unique_dates = len(set(comp[1] for comp in all_competitors))
        
        # Группируем по пользователям
        user_stats = defaultdict(int)
        date_stats = defaultdict(int)
        
        for comp in all_competitors:
            user_id = comp[0]
            date = comp[1]
            user_stats[user_id] += 1
            date_stats[date] += 1
        
        # Выводим общую статистику
        print("📈 ОБЩАЯ СТАТИСТИКА:")
        print(f"   🏁 Всего заездов: {total_races}")
        print(f"   👥 Уникальных пользователей: {unique_users}")
        print(f"   📅 Дней с заездами: {unique_dates}")
        print()
        
        # Топ пользователей
        print("🏆 ТОП ПОЛЬЗОВАТЕЛЕЙ:")
        sorted_users = sorted(user_stats.items(), key=lambda x: x[1], reverse=True)
        for i, (user_id, count) in enumerate(sorted_users[:10], 1):
            print(f"   {i:2d}. ID:{user_id} - {count} заездов")
        
        if len(sorted_users) > 10:
            print(f"   ... и ещё {len(sorted_users) - 10} пользователей")
        print()
        
        # Активные даты
        print("📅 АКТИВНЫЕ ДАТЫ:")
        sorted_dates = sorted(date_stats.items(), key=lambda x: x[1], reverse=True)
        for i, (date, count) in enumerate(sorted_dates[:10], 1):
            print(f"   {i:2d}. {date} - {count} заездов")
        
        if len(sorted_dates) > 10:
            print(f"   ... и ещё {len(sorted_dates) - 10} дней")
        
    except Exception as e:
        print(f"❌ Ошибка при чтении базы данных: {e}")


if __name__ == "__main__":
    main() 
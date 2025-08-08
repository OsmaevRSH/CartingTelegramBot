#!/usr/bin/env python3
"""
Скрипт для очистки базы данных бота
"""

import sys
import os
from pathlib import Path

# Добавляем корневую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import clear_db, init_db, DB_FILE


def main():
    """Основная функция для очистки БД"""
    print("🗑️  Скрипт очистки базы данных бота")
    print("=" * 40)
    
    # Проверяем, существует ли файл БД
    if not DB_FILE.exists():
        print("❌ Файл базы данных не найден:", DB_FILE)
        print("✅ База данных уже чиста (файл не существует)")
        return
    
    # Запрашиваем подтверждение
    print(f"📁 Файл базы данных: {DB_FILE}")
    print("\n⚠️  ВНИМАНИЕ: Это действие ПОЛНОСТЬЮ УДАЛИТ все данные!")
    print("   - Все сохранённые заезды")
    print("   - Всю статистику пользователей")
    print("   - Весь рейтинг")
    
    response = input("\n❓ Вы уверены, что хотите очистить базу данных? (да/нет): ").strip().lower()
    
    if response not in ['да', 'yes', 'y']:
        print("❌ Операция отменена")
        return
    
    # Дополнительное подтверждение для безопасности
    confirm = input("💀 Последнее предупреждение! Введите 'УДАЛИТЬ' для подтверждения: ").strip()
    
    if confirm != 'УДАЛИТЬ':
        print("❌ Операция отменена")
        return
    
    try:
        # Выполняем очистку
        print("\n🔄 Очистка базы данных...")
        clear_db()
        
        # Инициализируем заново
        print("🔄 Инициализация чистой базы данных...")
        init_db()
        
        print("✅ База данных успешно очищена!")
        print("🎉 Бот готов к работе с чистой базой данных")
        
    except Exception as e:
        print(f"❌ Ошибка при очистке базы данных: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
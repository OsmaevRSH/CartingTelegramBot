#!/usr/bin/env python3
"""
Скрипт для принудительной очистки базы данных бота БЕЗ подтверждений
ИСПОЛЬЗУЙТЕ ОСТОРОЖНО! Все данные будут удалены без возможности восстановления!
"""

import sys
import os
from pathlib import Path

# Добавляем корневую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import clear_db, init_db, DB_FILE


def main():
    """Принудительная очистка БД без подтверждений"""
    print("🗑️  Принудительная очистка базы данных бота")
    print("=" * 50)
    
    # Проверяем, существует ли файл БД
    if not DB_FILE.exists():
        print("❌ Файл базы данных не найден:", DB_FILE)
        print("✅ База данных уже чиста (файл не существует)")
        return
    
    print(f"📁 Файл базы данных: {DB_FILE}")
    print("⚠️  ВНИМАНИЕ: Выполняется принудительная очистка!")
    
    try:
        # Выполняем очистку
        print("🔄 Очистка базы данных...")
        clear_db()
        
        # Инициализируем заново
        print("🔄 Инициализация чистой базы данных...")
        init_db()
        
        print("✅ База данных принудительно очищена!")
        print("🎉 Бот готов к работе с чистой базой данных")
        
    except Exception as e:
        print(f"❌ Ошибка при очистке базы данных: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
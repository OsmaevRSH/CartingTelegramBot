#!/usr/bin/env python3
"""
Скрипт для очистки базы данных бота
"""
import sys
import os

# bot/utils/clear_database.py → bot/utils → bot → project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database.db import clear_db, init_db, DB_FILE


def main():
    """Основная функция для очистки БД"""
    print("🗑️  Скрипт очистки базы данных бота")
    print("=" * 40)

    if not DB_FILE.exists():
        print("❌ Файл базы данных не найден:", DB_FILE)
        print("✅ База данных уже чиста (файл не существует)")
        return

    print(f"📁 Файл базы данных: {DB_FILE}")
    print("\n⚠️  ВНИМАНИЕ: Это действие ПОЛНОСТЬЮ УДАЛИТ все данные!")
    print("   - Все сохранённые заезды")
    print("   - Всю статистику пользователей")
    print("   - Весь рейтинг")

    response = input("\n❓ Вы уверены, что хотите очистить базу данных? (да/нет): ").strip().lower()
    if response not in ['да', 'yes', 'y']:
        print("❌ Операция отменена")
        return

    confirm = input("💀 Последнее предупреждение! Введите 'УДАЛИТЬ' для подтверждения: ").strip()
    if confirm != 'УДАЛИТЬ':
        print("❌ Операция отменена")
        return

    try:
        print("\n🔄 Очистка базы данных...")
        clear_db()
        print("🔄 Инициализация чистой базы данных...")
        init_db()
        print("✅ База данных успешно очищена!")
        print("🎉 Бот готов к работе с чистой базой данных")
    except Exception as e:
        print(f"❌ Ошибка при очистке базы данных: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

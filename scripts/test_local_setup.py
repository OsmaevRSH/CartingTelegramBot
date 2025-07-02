#!/usr/bin/env python3
"""
Скрипт для тестирования локальной настройки проекта
"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Тестирует, что все модули корректно импортируются"""
    try:
        print("🧪 Тестирую импорты...")
        
        from src.models.models import Race, DayRaces, Cart, Competitor, ParsingError, LapData
        print("✅ Модели: OK")
        
        from src.parsers.parsers import ArchiveParser, RaceParser, FullRaceInfoParser
        print("✅ Парсеры: OK")
        
        from src.database.db import init_db, save_competitor, get_all_competitors
        print("✅ База данных: OK")
        
        from config.config import BOT_TOKEN, DATABASE_PATH, LOG_FILE
        print("✅ Конфигурация: OK")
        
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def test_config():
    """Тестирует конфигурацию"""
    try:
        print("\n🧪 Тестирую конфигурацию...")
        
        from config.config import BOT_TOKEN, DATABASE_PATH, LOG_FILE, LOG_LEVEL
        
        if not BOT_TOKEN:
            print("❌ BOT_TOKEN не настроен")
            return False
        
        if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            print("❌ BOT_TOKEN не заменен на реальный токен")
            return False
            
        print(f"✅ Токен бота: настроен ({BOT_TOKEN[:10]}...)")
        print(f"✅ База данных: {DATABASE_PATH}")
        print(f"✅ Лог файл: {LOG_FILE}")
        print(f"✅ Уровень логирования: {LOG_LEVEL}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return False

def test_directories():
    """Тестирует, что все необходимые директории существуют"""
    try:
        print("\n🧪 Тестирую директории...")
        
        required_dirs = [
            "src",
            "src/bot",
            "src/database", 
            "src/models",
            "src/parsers",
            "config",
            "scripts",
            "data",
            "logs"
        ]
        
        for dir_path in required_dirs:
            if Path(dir_path).exists():
                print(f"✅ {dir_path}: существует")
            else:
                print(f"❌ {dir_path}: не найдена")
                return False
                
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки директорий: {e}")
        return False

def test_files():
    """Тестирует, что все необходимые файлы существуют"""
    try:
        print("\n🧪 Тестирую файлы...")
        
        required_files = [
            "main.py",
            "requirements.txt",
            ".env",
            "config/config.py",
            "run_bot.sh",
            "docker-compose.yml"
        ]
        
        for file_path in required_files:
            if Path(file_path).exists():
                print(f"✅ {file_path}: существует")
            else:
                print(f"❌ {file_path}: не найден")
                return False
                
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки файлов: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование локальной настройки CartingBot")
    print("=" * 50)
    
    all_tests_passed = True
    
    # Тест директорий
    if not test_directories():
        all_tests_passed = False
    
    # Тест файлов
    if not test_files():
        all_tests_passed = False
    
    # Тест импортов
    if not test_imports():
        all_tests_passed = False
    
    # Тест конфигурации
    if not test_config():
        all_tests_passed = False
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("✅ Все тесты пройдены! Проект готов к запуску")
        print("🚀 Запустите бота командой: ./run_bot.sh")
        sys.exit(0)
    else:
        print("❌ Некоторые тесты не пройдены!")
        print("🔧 Исправьте ошибки и запустите тест снова")
        sys.exit(1)

if __name__ == "__main__":
    main() 
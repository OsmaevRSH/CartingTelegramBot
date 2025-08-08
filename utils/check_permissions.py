#!/usr/bin/env python3
"""
Скрипт для проверки прав доступа к файлам и директориям
"""

import os
import sys
import stat
from pathlib import Path

def check_permissions(path, check_write=True):
    """Проверяет права доступа к файлу или директории"""
    try:
        path_obj = Path(path)
        
        if not path_obj.exists():
            return False, f"Не существует"
        
        # Получаем статистику файла
        st = path_obj.stat()
        mode = st.st_mode
        
        # Проверяем права доступа
        readable = os.access(path, os.R_OK)
        writable = os.access(path, os.W_OK) if check_write else True
        executable = os.access(path, os.X_OK) if path_obj.is_file() else os.access(path, os.X_OK)
        
        # Форматируем права в виде rwx
        permissions = stat.filemode(mode)
        
        status = "✅" if (readable and writable and executable) else "❌"
        details = f"{permissions} (R:{readable}, W:{writable}, X:{executable})"
        
        return True, f"{status} {details}"
        
    except Exception as e:
        return False, f"❌ Ошибка: {e}"

def main():
    """Основная функция для проверки прав доступа"""
    print("🔍 Проверка прав доступа CartingBot")
    print("=" * 50)
    
    # Список важных файлов и директорий для проверки
    paths_to_check = [
        ("data/", True),
        ("logs/", True),
        ("config/", True),
        ("scripts/", True),
        ("src/", False),
        ("data/races.db", True),
        ("scripts/health_check.py", False),
        ("scripts/manage.sh", False),
        ("scripts/deploy.sh", False),
        ("scripts/clear_database.py", False),
        ("main.py", False),
        ("docker-compose.yml", False),
        ("docker/Dockerfile", False),
        ("docker/entrypoint.sh", False),
    ]
    
    all_ok = True
    
    for path, check_write in paths_to_check:
        exists, status = check_permissions(path, check_write)
        
        if exists:
            print(f"📁 {path:<25} {status}")
        else:
            print(f"📁 {path:<25} ⚠️  {status}")
            if path.endswith("/") or path in ["data/races.db"]:
                # Для директорий и критичных файлов это может быть проблемой
                continue
            all_ok = False
    
    print("\n" + "=" * 50)
    
    if all_ok:
        print("✅ Все критичные файлы и директории доступны!")
    else:
        print("❌ Обнаружены проблемы с доступом к файлам!")
        
    # Дополнительная информация
    print(f"\n📊 Текущий пользователь: {os.getuid()}:{os.getgid()}")
    print(f"📊 Рабочая директория: {os.getcwd()}")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main()) 
#!/bin/bash

# Entrypoint script для CartingBot

set -e

echo "🚀 Запуск CartingBot..."

# Проверяем и создаем необходимые директории
echo "📁 Создаю необходимые директории..."
mkdir -p /app/data /app/logs /app/config

# Устанавливаем максимальные права доступа на ВСЕ файлы и директории
echo "🔧 Устанавливаю максимальные права доступа на все файлы и папки..."

# Права 777 для всех директорий и файлов данных
chmod -R 777 /app/data /app/logs 2>/dev/null || true
chown -R root:root /app/data /app/logs 2>/dev/null || true

# Права 755 для всех файлов и папок в /app (включая исходный код)
chmod -R 755 /app 2>/dev/null || true
chown -R root:root /app 2>/dev/null || true

# Максимальные права для критичных директорий
chmod -R 777 /app/data 2>/dev/null || true
chmod -R 777 /app/logs 2>/dev/null || true
chmod -R 777 /app/config 2>/dev/null || true

# Убеждаемся, что все скрипты исполняемы
chmod +x /app/utils/*.py 2>/dev/null || true
chmod +x /app/main.py 2>/dev/null || true

# Максимальные права для Python файлов
find /app -name "*.py" -exec chmod 755 {} \; 2>/dev/null || true

# Максимальные права для всех файлов в src/
chmod -R 755 /app/src 2>/dev/null || true

# Создаем файл базы данных с максимальными правами если не существует
if [ ! -f /app/data/races.db ]; then
    touch /app/data/races.db
    chmod 777 /app/data/races.db 2>/dev/null || true
    chown root:root /app/data/races.db 2>/dev/null || true
fi

# Проверяем наличие config файлов
echo "🔧 Проверяю конфигурацию..."

if [ ! -f /app/config/__init__.py ]; then
    echo "📝 Создаю config/__init__.py..."
    echo "# Config package for CartingBot" > /app/config/__init__.py
    chmod 777 /app/config/__init__.py 2>/dev/null || true
fi

if [ ! -f /app/config/config.py ]; then
    echo "📝 Создаю config/config.py из примера..."
    if [ -f /app/config/config.py.example ]; then
        cp /app/config/config.py.example /app/config/config.py
        chmod 777 /app/config/config.py 2>/dev/null || true
    else
        echo "❌ Файл config/config.py.example не найден!"
        exit 1
    fi
fi

# Проверяем BOT_TOKEN
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ Переменная окружения BOT_TOKEN не установлена!"
    echo "Добавьте BOT_TOKEN в .env файл или переменные окружения"
    exit 1
fi

# Запуск скрипта для установки максимальных прав доступа
echo "🔐 Запускаю скрипт установки максимальных прав доступа..."
# Permissions are now handled automatically in this script

echo "✅ Конфигурация проверена"
echo "✅ Максимальные права доступа установлены автоматически"
echo "👤 Запуск от пользователя: $(whoami) ($(id))"

# Запускаем основное приложение
echo "🤖 Запускаю бота..."
exec python main.py 
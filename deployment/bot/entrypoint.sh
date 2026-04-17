#!/bin/bash
set -e

echo "🚀 Запуск CartingBot..."

mkdir -p /app/data /app/logs
chmod -R 777 /app/data /app/logs 2>/dev/null || true

if [ ! -f /app/data/races.db ]; then
    touch /app/data/races.db
    chmod 777 /app/data/races.db 2>/dev/null || true
fi

if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN не установлен!"
    exit 1
fi

echo "✅ Конфигурация проверена"
echo "🤖 Запуск бота..."
exec python bot/main.py

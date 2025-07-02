#!/bin/bash

# Скрипт для исправления проблем с конфигурацией

set -e

echo "🔧 Исправление проблем с конфигурацией CartingBot..."

# Проверяем, что мы в правильной директории
if [ ! -f "main.py" ]; then
    echo "❌ Не найден main.py. Запустите скрипт из корневой директории проекта"
    exit 1
fi

# Создаем config/__init__.py если не существует
if [ ! -f "config/__init__.py" ]; then
    echo "📝 Создаю config/__init__.py..."
    echo "# Config package for CartingBot" > config/__init__.py
    echo "✅ Файл config/__init__.py создан"
else
    echo "✅ Файл config/__init__.py уже существует"
fi

# Создаем config/config.py если не существует
if [ ! -f "config/config.py" ]; then
    echo "📝 Создаю config/config.py из примера..."
    
    if [ -f "config/config.py.example" ]; then
        cp config/config.py.example config/config.py
        echo "✅ Файл config/config.py создан"
    else
        echo "❌ Файл config/config.py.example не найден"
        exit 1
    fi
else
    echo "✅ Файл config/config.py уже существует"
fi

# Проверяем файл .env
if [ ! -f ".env" ]; then
    echo "📝 Создаю .env из примера..."
    
    if [ -f "env.example" ]; then
        cp env.example .env
        echo "✅ Файл .env создан"
        echo "⚠️  Не забудьте настроить BOT_TOKEN в файле .env"
    else
        echo "❌ Файл env.example не найден"
        exit 1
    fi
else
    echo "✅ Файл .env уже существует"
fi

# Проверяем BOT_TOKEN в .env
if grep -q "YOUR_BOT_TOKEN_HERE" .env 2>/dev/null; then
    echo "⚠️  BOT_TOKEN не настроен в файле .env"
    echo "   Отредактируйте файл .env и замените YOUR_BOT_TOKEN_HERE на реальный токен"
else
    echo "✅ BOT_TOKEN настроен в .env"
fi

# Создаем необходимые директории
echo "📁 Создаю необходимые директории..."
mkdir -p data logs
echo "✅ Директории созданы"

# Если используется Docker, пересобираем образ
if [ -f "docker-compose.yml" ]; then
    echo ""
    echo "🐳 Обнаружен Docker Compose файл"
    echo "   Для применения изменений выполните:"
    echo "   ./scripts/manage.sh update"
    echo ""
fi

echo "✅ Исправление конфигурации завершено!"
echo ""
echo "🚀 Теперь можете запустить бота:"
echo "   Локально: ./run_bot.sh"
echo "   Docker:   ./scripts/manage.sh start" 
#!/bin/bash

# Скрипт для установки максимальных прав доступа для всех файлов и папок

set -e

echo "🔧 Установка максимальных прав доступа..."
echo "=================================================="

# Устанавливаем права 777 для всех критичных директорий
echo "📁 Устанавливаю права 777 для директорий данных..."
chmod -R 777 /app/data 2>/dev/null || true
chmod -R 777 /app/logs 2>/dev/null || true
chmod -R 777 /app/config 2>/dev/null || true

# Устанавливаем права 755 для всех файлов кода
echo "📄 Устанавливаю права 755 для файлов кода..."
chmod -R 755 /app/src 2>/dev/null || true
chmod -R 755 /app/scripts 2>/dev/null || true

# Делаем исполняемыми все Python и shell скрипты
echo "🔧 Делаю исполняемыми все скрипты..."
find /app -type f -name "*.py" -exec chmod +x {} \; 2>/dev/null || true
find /app -type f -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true

# Устанавливаем максимальные права для конкретных файлов
echo "🔐 Устанавливаю максимальные права для критичных файлов..."
chmod 777 /app/data/*.db 2>/dev/null || true
chmod 777 /app/logs/*.log 2>/dev/null || true
chmod 777 /app/config/*.py 2>/dev/null || true

# Устанавливаем владельца root для всех файлов
echo "👤 Устанавливаю владельца root для всех файлов..."
chown -R root:root /app 2>/dev/null || true

# Создаем файлы с правильными правами если не существуют
echo "📝 Создаю файлы с правильными правами..."
if [ ! -f /app/data/races.db ]; then
    touch /app/data/races.db
    chmod 777 /app/data/races.db
    chown root:root /app/data/races.db
fi

if [ ! -f /app/logs/bot.log ]; then
    touch /app/logs/bot.log
    chmod 777 /app/logs/bot.log
    chown root:root /app/logs/bot.log
fi

# Финальная установка максимальных прав
echo "🎯 Применяю финальные максимальные права..."
chmod 777 /app/data/* 2>/dev/null || true
chmod 777 /app/logs/* 2>/dev/null || true
chmod 777 /app/config/* 2>/dev/null || true

echo "✅ Максимальные права доступа установлены для всех файлов и папок!"
echo "👤 Текущий пользователь: $(whoami) ($(id))"
echo ""
echo "🔍 Проверка критичных файлов:"
ls -la /app/data/ 2>/dev/null || echo "❌ Папка data не найдена"
ls -la /app/logs/ 2>/dev/null || echo "❌ Папка logs не найдена"
ls -la /app/config/ 2>/dev/null || echo "❌ Папка config не найдена"

echo ""
echo "🎉 Установка прав завершена!" 
#!/bin/bash

# Скрипт для развертывания CartingBot на сервере

set -e

echo "🚀 Развертывание CartingBot..."

# Проверяем, что Docker установлен
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Устанавливаю Docker..."
    
    # Обновляем пакеты
    sudo apt-get update
    
    # Устанавливаем необходимые пакеты
    sudo apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # Добавляем официальный GPG ключ Docker
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Добавляем репозиторий Docker
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Обновляем пакеты и устанавливаем Docker
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # Добавляем пользователя в группу docker
    sudo usermod -aG docker $USER
    
    echo "✅ Docker установлен успешно!"
    echo "⚠️  Перезайдите в систему для применения изменений в группе docker"
fi

# Проверяем, что Docker Compose установлен
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Устанавливаю..."
    
    # Скачиваем и устанавливаем Docker Compose
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    echo "✅ Docker Compose установлен успешно!"
fi

# Проверяем наличие файла .env
if [ ! -f "../.env" ]; then
    echo "❌ Файл .env не найден!"
    echo "Создайте файл .env на основе env.example:"
    echo "cp env.example .env"
    echo "и заполните его вашими настройками"
    exit 1
fi

# Создаем необходимые директории
mkdir -p data logs

# Останавливаем и удаляем старые контейнеры
echo "🔄 Останавливаю старые контейнеры..."
docker-compose down --remove-orphans

# Собираем и запускаем новые контейнеры
echo "🔨 Собираю и запускаю контейнеры..."
docker-compose up -d --build

# Проверяем статус
echo "✅ Развертывание завершено!"
echo "📊 Статус контейнеров:"
docker-compose ps

echo ""
echo "🎉 CartingBot успешно развернут!"
echo "📝 Логи можно посмотреть командой: docker-compose logs -f"
echo "🔄 Для перезапуска используйте: docker-compose restart"
echo "🛑 Для остановки используйте: docker-compose down" 
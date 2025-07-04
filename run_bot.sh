#!/bin/bash

# Скрипт для локального запуска CartingBot в виртуальном окружении

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Запуск CartingBot (локально)${NC}"

# Проверяем, что мы находимся в правильной директории
if [ ! -f "main.py" ]; then
    echo -e "${RED}❌ Файл main.py не найден. Убедитесь, что вы находитесь в корневой директории проекта${NC}"
    exit 1
fi

# Проверяем наличие виртуального окружения
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Виртуальное окружение не найдено. Создаю новое...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Не удалось создать виртуальное окружение${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Виртуальное окружение создано${NC}"
fi

# Активируем виртуальное окружение
echo -e "${BLUE}🔧 Активирую виртуальное окружение...${NC}"
source venv/bin/activate

# Проверяем наличие pip
if ! command -v pip &> /dev/null; then
    echo -e "${RED}❌ pip не найден в виртуальном окружении${NC}"
    exit 1
fi

# Устанавливаем/обновляем зависимости
echo -e "${BLUE}📦 Устанавливаю зависимости...${NC}"
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Не удалось установить зависимости${NC}"
    exit 1
fi

# Проверяем наличие файла .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Файл .env не найден!${NC}"
    echo -e "${YELLOW}Создаю файл .env на основе env.example...${NC}"
    
    if [ -f "env.example" ]; then
        cp env.example .env
        echo -e "${GREEN}✅ Файл .env создан${NC}"
        echo -e "${YELLOW}📝 Отредактируйте файл .env и добавьте токен бота:${NC}"
        echo -e "${YELLOW}   nano .env${NC}"
        echo -e "${YELLOW}   Замените YOUR_BOT_TOKEN_HERE на реальный токен${NC}"
        echo -e "${YELLOW}   Затем снова запустите скрипт${NC}"
        exit 1
    else
        echo -e "${RED}❌ Файл env.example не найден${NC}"
        exit 1
    fi
fi

# Загружаем переменные окружения
echo -e "${BLUE}⚙️  Загружаю переменные окружения...${NC}"
set -a
source .env
set +a

# Проверяем наличие токена бота
if [ -z "$BOT_TOKEN" ] || [ "$BOT_TOKEN" = "YOUR_BOT_TOKEN_HERE" ]; then
    echo -e "${RED}❌ Токен бота не настроен!${NC}"
    echo -e "${YELLOW}Отредактируйте файл .env и добавьте правильный токен бота${NC}"
    echo -e "${YELLOW}Пример:${NC}"
    echo -e "${YELLOW}   BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz${NC}"
    exit 1
fi

# Создаем необходимые директории
echo -e "${BLUE}📁 Создаю необходимые директории...${NC}"
mkdir -p data logs

# Проверяем наличие основного файла конфигурации
if [ ! -f "config/config.py" ]; then
    echo -e "${YELLOW}⚠️  Файл config/config.py не найден. Создаю на основе примера...${NC}"
    if [ -f "config/config.py.example" ]; then
        cp config/config.py.example config/config.py
        echo -e "${GREEN}✅ Файл config/config.py создан${NC}"
    else
        echo -e "${RED}❌ Файл config/config.py.example не найден${NC}"
        exit 1
    fi
fi

# Тестируем подключение к сайту
echo -e "${BLUE}🌐 Проверяю подключение к сайту kartchrono.com...${NC}"
if command -v curl &> /dev/null; then
    if curl -s --max-time 10 https://mayak.kartchrono.com/archive/ > /dev/null; then
        echo -e "${GREEN}✅ Сайт доступен${NC}"
    else
        echo -e "${YELLOW}⚠️  Сайт недоступен или медленно отвечает${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  curl не найден, пропускаю проверку сайта${NC}"
fi

# Показываем информацию о конфигурации
echo -e "${BLUE}📋 Информация о конфигурации:${NC}"
echo -e "   📁 База данных: ${DATABASE_PATH:-data/races.db}"
echo -e "   📝 Логи: ${LOG_FILE:-logs/bot.log}"
echo -e "   🔧 Уровень логирования: ${LOG_LEVEL:-INFO}"

# Запускаем бота
echo ""
echo -e "${GREEN}🤖 Запускаю бота...${NC}"
echo -e "${YELLOW}Для остановки нажмите Ctrl+C${NC}"
echo "================================"

# Устанавливаем обработчик сигналов для корректного завершения
trap 'echo -e "\n${YELLOW}🛑 Получен сигнал остановки, завершаю работу...${NC}"; deactivate; exit 0' SIGINT SIGTERM

# Запускаем основной файл
python main.py

# Деактивируем виртуальное окружение при выходе
deactivate

echo -e "${GREEN}✅ Бот завершил работу${NC}" 
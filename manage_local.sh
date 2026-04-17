#!/bin/bash

# Скрипт для управления CartingBot локально (venv)

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Определяем пути для разных ОС
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    VENV_PYTHON="venv/Scripts/python"
    VENV_PIP="venv/Scripts/pip"
    ACTIVATE_CMD="venv/Scripts/activate"
else
    # Unix/Linux/Mac
    VENV_PYTHON="venv/bin/python"
    VENV_PIP="venv/bin/pip"
    ACTIVATE_CMD="venv/bin/activate"
fi

function colored_echo() {
    echo -e "${2}${1}${NC}"
}

function check_venv() {
    if [ ! -d "venv" ]; then
        colored_echo "⚠️  Виртуальное окружение не найдено. Создаю новое..." $YELLOW
        python3 -m venv venv
        if [ $? -ne 0 ]; then
            colored_echo "❌ Не удалось создать виртуальное окружение" $RED
            exit 1
        fi
        colored_echo "✅ Виртуальное окружение создано" $GREEN
    fi
}

function install_deps() {
    colored_echo "📦 Устанавливаю зависимости..." $BLUE
    $VENV_PIP install -r requirements.txt > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        colored_echo "❌ Не удалось установить зависимости" $RED
        exit 1
    fi
}

function check_env() {
    if [ ! -f ".env" ]; then
        colored_echo "❌ Файл .env не найден!" $RED
        colored_echo "Создайте файл .env на основе env.example:" $YELLOW
        colored_echo "cp env.example .env" $BLUE
        exit 1
    fi
}

function create_dirs() {
    mkdir -p data logs config
}

function show_help() {
    colored_echo "🤖 CartingBot - Локальное управление (venv)" $GREEN
    echo ""
    echo "Использование: ./manage_local.sh [команда]"
    echo ""
    echo "Команды:"
    echo "  start        - Запустить бота"
    echo "  api          - Запустить FastAPI бэкенд"
    echo "  webapp       - Запустить React frontend (dev)"
    echo "  clear-db     - Очистить базу данных"
    echo "  health       - Проверить здоровье системы"
    echo "  help         - Показать эту справку"
    echo ""
}

function start_bot() {
    colored_echo "🚀 Запуск CartingBot (локально)" $GREEN
    check_venv
    install_deps
    check_env
    create_dirs
    colored_echo "🤖 Запускаю бота..." $BLUE
    $VENV_PYTHON bot/main.py
}

function start_api() {
    colored_echo "🌐 Запуск FastAPI бэкенда (локально)" $GREEN
    check_venv
    install_deps
    check_env
    create_dirs
    colored_echo "🚀 Запускаю API на http://localhost:8000 ..." $BLUE
    $VENV_PYTHON -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
}

function start_webapp() {
    colored_echo "⚛️  Запуск React webapp (dev)" $GREEN
    if [ ! -d "webapp/node_modules" ]; then
        colored_echo "📦 Устанавливаю npm-зависимости..." $BLUE
        cd webapp && npm install && cd ..
    fi
    colored_echo "🌐 Запускаю webapp на http://localhost:5173 ..." $BLUE
    cd webapp && npm run dev
}

function clear_database() {
    colored_echo "🗑️  Очистка базы данных..." $YELLOW
    check_venv
    install_deps
    $VENV_PYTHON bot/utils/clear_database.py
}

function health_check() {
    colored_echo "🏥 Проверка здоровья системы..." $BLUE
    check_venv
    install_deps
    $VENV_PYTHON bot/utils/health_check.py
}

# Основная логика
case "${1:-help}" in
    start)
        start_bot
        ;;
    api)
        start_api
        ;;
    webapp)
        start_webapp
        ;;
    clear-db)
        clear_database
        ;;
    health)
        health_check
        ;;
    help)
        show_help
        ;;
    *)
        colored_echo "❌ Неизвестная команда: $1" $RED
        show_help
        exit 1
        ;;
esac
#!/bin/bash

# Скрипт для управления CartingBot на сервере (Docker)

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function colored_echo() {
    echo -e "${2}${1}${NC}"
}

function check_docker() {
    if ! command -v docker-compose &> /dev/null; then
        colored_echo "❌ docker-compose не найден" $RED
        exit 1
    fi
}

function show_help() {
    colored_echo "🤖 CartingBot - Удаленное управление (Docker)" $GREEN
    echo ""
    echo "Использование: ./manage_remote.sh [команда]"
    echo ""
    echo "Команды:"
    echo "  start        - Запустить бота"
    echo "  stop         - Остановить бота"
    echo "  restart      - Перезапустить бота"
    echo "  status       - Показать статус бота"
    echo "  logs         - Показать логи бота"
    echo "  logs-f       - Показать логи в реальном времени"
    echo "  update       - Обновить и перезапустить бота"
    echo "  shell        - Войти в контейнер бота"
    echo "  clean        - Удалить все данные и контейнеры"
    echo "  backup       - Создать резервную копию базы данных"
    echo "  clear-db     - Очистить базу данных"
    echo "  check-perm   - Проверить права доступа"
    echo "  health       - Проверить здоровье системы"
    echo "  help         - Показать эту справку"
    echo ""
}

function start_bot() {
    colored_echo "🚀 Запускаю бота..." $BLUE
    cd deployment
    docker-compose up -d
    if [ $? -eq 0 ]; then
        colored_echo "✅ Бот запущен!" $GREEN
    else
        colored_echo "❌ Не удалось запустить бота" $RED
    fi
    cd ..
}

function stop_bot() {
    colored_echo "🛑 Останавливаю бота..." $BLUE
    cd deployment
    docker-compose down
    if [ $? -eq 0 ]; then
        colored_echo "✅ Бот остановлен!" $GREEN
    else
        colored_echo "❌ Не удалось остановить бота" $RED
    fi
    cd ..
}

function restart_bot() {
    colored_echo "🔄 Перезапускаю бота..." $BLUE
    cd deployment
    docker-compose restart
    if [ $? -eq 0 ]; then
        colored_echo "✅ Бот перезапущен!" $GREEN
    else
        colored_echo "❌ Не удалось перезапустить бота" $RED
    fi
    cd ..
}

function show_status() {
    colored_echo "📊 Статус бота:" $BLUE
    cd deployment
    docker-compose ps
    cd ..
}

function show_logs() {
    colored_echo "📝 Логи бота:" $BLUE
    cd deployment
    docker-compose logs --tail=50
    cd ..
}

function show_logs_follow() {
    colored_echo "📝 Логи бота (в реальном времени):" $BLUE
    cd deployment
    docker-compose logs -f
    cd ..
}

function update_bot() {
    colored_echo "🔄 Обновляю и перезапускаю бота..." $BLUE
    cd deployment
    docker-compose down
    docker-compose up -d --build
    if [ $? -eq 0 ]; then
        colored_echo "✅ Бот обновлен и перезапущен!" $GREEN
    else
        colored_echo "❌ Не удалось обновить бота" $RED
    fi
    cd ..
}

function shell_bot() {
    colored_echo "🐚 Вход в контейнер бота..." $BLUE
    cd deployment
    docker-compose exec carting-bot bash
    cd ..
}

function clean_bot() {
    colored_echo "⚠️  Удаление всех данных и контейнеров..." $YELLOW
    read -p "Вы уверены? Все данные будут удалены! (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd deployment
        docker-compose down -v --remove-orphans
        docker system prune -f
        cd ..
        rm -rf data logs
        colored_echo "✅ Все данные удалены!" $GREEN
    else
        colored_echo "❌ Отменено" $YELLOW
    fi
}

function backup_bot() {
    colored_echo "💾 Создаю резервную копию базы данных..." $BLUE
    if [ -f "data/races.db" ]; then
        backup_file="backups/races_backup_$(date +%Y%m%d_%H%M%S).db"
        mkdir -p backups
        cp data/races.db "$backup_file"
        colored_echo "✅ Резервная копия создана: $backup_file" $GREEN
    else
        colored_echo "❌ База данных не найдена!" $RED
    fi
}

function clear_database() {
    colored_echo "🗑️  Очистка базы данных..." $BLUE
    cd deployment
    docker-compose exec carting-bot python utils/clear_database.py
    cd ..
}

function check_permissions() {
    colored_echo "🔍 Проверка прав доступа..." $BLUE
    cd deployment
    docker-compose exec carting-bot python utils/check_permissions.py
    cd ..
}

function health_check() {
    colored_echo "🏥 Проверка здоровья системы..." $BLUE
    cd deployment
    docker-compose exec carting-bot python utils/health_check.py
    cd ..
}

# Проверяем наличие docker-compose
check_docker

# Основная логика
case "${1:-help}" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    logs-f)
        show_logs_follow
        ;;
    update)
        update_bot
        ;;
    shell)
        shell_bot
        ;;
    clean)
        clean_bot
        ;;
    backup)
        backup_bot
        ;;
    clear-db)
        clear_database
        ;;
    check-perm)
        check_permissions
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
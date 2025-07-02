#!/bin/bash

# Скрипт для управления CartingBot

function show_help() {
    echo "🤖 CartingBot - Управление ботом"
    echo ""
    echo "Использование: $0 [команда]"
    echo ""
    echo "Команды:"
    echo "  start      - Запустить бота"
    echo "  stop       - Остановить бота"
    echo "  restart    - Перезапустить бота"
    echo "  status     - Показать статус бота"
    echo "  logs       - Показать логи бота"
    echo "  logs-f     - Показать логи в реальном времени"
    echo "  update     - Обновить и перезапустить бота"
    echo "  shell      - Войти в контейнер бота"
    echo "  clean      - Удалить все данные и контейнеры"
    echo "  backup     - Создать резервную копию базы данных"
    echo "  fix-config - Исправить проблемы с конфигурацией"
    echo ""
}

function start_bot() {
    echo "🚀 Запускаю бота..."
    docker-compose up -d
    echo "✅ Бот запущен!"
}

function stop_bot() {
    echo "🛑 Останавливаю бота..."
    docker-compose down
    echo "✅ Бот остановлен!"
}

function restart_bot() {
    echo "🔄 Перезапускаю бота..."
    docker-compose restart
    echo "✅ Бот перезапущен!"
}

function show_status() {
    echo "📊 Статус бота:"
    docker-compose ps
}

function show_logs() {
    echo "📝 Логи бота:"
    docker-compose logs --tail=50
}

function show_logs_follow() {
    echo "📝 Логи бота (в реальном времени):"
    docker-compose logs -f
}

function update_bot() {
    echo "🔄 Обновляю и перезапускаю бота..."
    docker-compose down
    docker-compose up -d --build
    echo "✅ Бот обновлен и перезапущен!"
}

function shell_bot() {
    echo "🐚 Вход в контейнер бота..."
    docker-compose exec carting-bot bash
}

function clean_bot() {
    echo "⚠️  Удаление всех данных и контейнеров..."
    read -p "Вы уверены? Все данные будут удалены! (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v --remove-orphans
        docker system prune -f
        rm -rf data logs
        echo "✅ Все данные удалены!"
    else
        echo "❌ Отменено"
    fi
}

function backup_bot() {
    echo "💾 Создаю резервную копию базы данных..."
    if [ -f "data/races.db" ]; then
        backup_file="backups/races_backup_$(date +%Y%m%d_%H%M%S).db"
        mkdir -p backups
        cp data/races.db "$backup_file"
        echo "✅ Резервная копия создана: $backup_file"
    else
        echo "❌ База данных не найдена!"
    fi
}

function fix_config() {
    echo "🔧 Исправляю проблемы с конфигурацией..."
    ./scripts/fix_config.sh
}

# Основная логика
case "$1" in
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
    fix-config)
        fix_config
        ;;
    *)
        show_help
        ;;
esac 
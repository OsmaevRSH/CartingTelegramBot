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
    if command -v docker-compose &> /dev/null; then
        DC="docker-compose"
    elif docker compose version &> /dev/null 2>&1; then
        DC="docker compose"
    else
        colored_echo "❌ docker-compose не найден. Установите Docker Compose v1 или Docker с плагином Compose v2." $RED
        exit 1
    fi
}

function show_help() {
    colored_echo "🤖 CartingBot - Удаленное управление (Docker)" $GREEN
    echo ""
    echo "Использование: ./manage_remote.sh [команда]"
    echo ""
    echo "Команды:"
    echo "  start        - Запустить все сервисы (бот + API + webapp)"
    echo "  stop         - Остановить все сервисы"
    echo "  restart      - Перезапустить все сервисы"
    echo "  status       - Показать статус сервисов"
    echo "  logs         - Показать логи"
    echo "  logs-f       - Показать логи в реальном времени"
    echo "  update       - Собрать и перезапустить сервисы без Git pull"
    echo "  full-update  - Безопасно: бэкап БД, Git pull и полное пересоздание сервисов"
    echo "  shell        - Войти в контейнер бота"
    echo "  shell-api    - Войти в контейнер API"
    echo "  clean        - Удалить все данные и контейнеры"
    echo "  backup       - Создать резервную копию базы данных"
    echo "  clear-db     - Очистить базу данных"
    echo "  health       - Проверить здоровье системы"
    echo "  help         - Показать эту справку"
    echo ""
}

function start_bot() {
    colored_echo "🚀 Запускаю бота..." $BLUE
    cd deployment
    $DC up -d
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
    $DC down
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
    $DC restart
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
    $DC ps
    cd ..
}

function show_logs() {
    colored_echo "📝 Логи бота:" $BLUE
    cd deployment
    $DC logs --tail=50
    cd ..
}

function show_logs_follow() {
    colored_echo "📝 Логи бота (в реальном времени):" $BLUE
    cd deployment
    $DC logs -f
    cd ..
}

function update_bot() {
    colored_echo "🔄 Обновляю и перезапускаю бота..." $BLUE
    cd deployment
    if [ ! -f ../secrets/xray-telegram.json ]; then
        colored_echo "❌ Не найден секретный конфиг Xray: ../secrets/xray-telegram.json" $RED
        cd ..
        return 1
    fi
    $DC up -d --build
    if [ $? -eq 0 ]; then
        colored_echo "✅ Бот обновлен и перезапущен!" $GREEN
    else
        colored_echo "❌ Не удалось обновить бота" $RED
    fi
    cd ..
}

function full_update() {
    local database_path="data/races.db"
    local backup_dir="backups"
    local timestamp
    local backup_file
    local temporary_backup

    colored_echo "🛡️  Запускаю безопасное полное обновление..." $BLUE

    if [ ! -f "$database_path" ]; then
        colored_echo "❌ База данных не найдена: $database_path. Обновление отменено." $RED
        return 1
    fi

    if [ ! -f "secrets/xray-telegram.json" ]; then
        colored_echo "❌ Не найден секретный конфиг Xray: secrets/xray-telegram.json. Обновление отменено." $RED
        return 1
    fi

    if [ ! -r "secrets/xray-telegram.json" ]; then
        colored_echo "❌ Нет прав на чтение secrets/xray-telegram.json. Обновление отменено." $RED
        return 1
    fi

    if ! git diff --quiet -- . ':(exclude)data/races.db' || \
       ! git diff --cached --quiet -- . ':(exclude)data/races.db'; then
        colored_echo "❌ Есть незакоммиченные изменения кода. Обновление отменено, чтобы ничего не перезаписать." $RED
        return 1
    fi

    if [ -n "$(git ls-files --others --exclude-standard)" ]; then
        colored_echo "❌ Есть неотслеживаемые файлы. Обновление отменено, чтобы Git pull не затёр их." $RED
        return 1
    fi

    mkdir -p "$backup_dir"
    timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
    backup_file="$backup_dir/races-before-full-update-$timestamp.db"
    temporary_backup="$backup_file.tmp"
    umask 077

    if ! python3 - "$database_path" "$temporary_backup" <<'PY'
import sqlite3
import sys

source_path, backup_path = sys.argv[1:]
source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
destination = sqlite3.connect(backup_path)
try:
    source.backup(destination)
    result = destination.execute("PRAGMA integrity_check").fetchone()[0]
    if result != "ok":
        raise RuntimeError(f"SQLite integrity_check failed: {result}")
finally:
    destination.close()
    source.close()
PY
    then
        rm -f "$temporary_backup"
        colored_echo "❌ Не удалось создать проверенный бэкап БД. Обновление отменено." $RED
        return 1
    fi

    mv "$temporary_backup" "$backup_file"
    colored_echo "✅ Проверенный бэкап БД создан: $backup_file" $GREEN

    if ! git fetch --prune origin main || ! git pull --ff-only origin main; then
        colored_echo "❌ Git pull не выполнен. Контейнеры и рабочая БД не менялись." $RED
        return 1
    fi

    cd deployment || return 1
    if ! $DC config -q; then
        colored_echo "❌ Docker Compose конфигурация невалидна. Контейнеры и рабочая БД не менялись." $RED
        cd ..
        return 1
    fi

    if ! $DC run --rm --no-deps --entrypoint xray carting-xray run -test -c /etc/xray/config.json; then
        colored_echo "❌ Конфигурация Xray невалидна. Контейнеры и рабочая БД не менялись." $RED
        cd ..
        return 1
    fi

    if ! $DC up -d --build --force-recreate --remove-orphans; then
        colored_echo "❌ Сервисы не удалось пересоздать. Бэкап сохранён: ../$backup_file" $RED
        cd ..
        return 1
    fi

    if ! wait_for_service_health "carting-xray" 60 || ! wait_for_service_health "carting-bot" 90; then
        colored_echo "❌ Сервисы пересозданы, но не прошли healthcheck. Бэкап сохранён: ../$backup_file" $RED
        cd ..
        return 1
    fi

    if ! $DC exec -T carting-api python -c 'from urllib.request import urlopen; assert urlopen("http://127.0.0.1:8000/health", timeout=10).status == 200'; then
        colored_echo "❌ API не прошёл проверку здоровья. Бэкап сохранён: ../$backup_file" $RED
        cd ..
        return 1
    fi

    cd ..
    if ! python3 - "$database_path" <<'PY'
import sqlite3
import sys

connection = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
try:
    result = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if result != "ok":
        raise RuntimeError(f"SQLite integrity_check failed: {result}")
finally:
    connection.close()
PY
    then
        colored_echo "❌ После обновления БД не прошла integrity_check. Используйте бэкап: $backup_file" $RED
        return 1
    fi

    colored_echo "✅ Полное обновление завершено. Бэкап БД: $backup_file" $GREEN
}

function wait_for_service_health() {
    local service_name="$1"
    local timeout_seconds="$2"
    local elapsed=0
    local container_id
    local health_status

    while [ "$elapsed" -lt "$timeout_seconds" ]; do
        container_id="$($DC ps -q "$service_name")"
        if [ -n "$container_id" ]; then
            health_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id")"
            if [ "$health_status" = "healthy" ] || [ "$health_status" = "running" ]; then
                return 0
            fi
            if [ "$health_status" = "unhealthy" ] || [ "$health_status" = "exited" ] || [ "$health_status" = "dead" ]; then
                colored_echo "❌ $service_name: $health_status" $RED
                return 1
            fi
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done

    colored_echo "❌ Таймаут healthcheck для $service_name" $RED
    return 1
}

function shell_bot() {
    colored_echo "🐚 Вход в контейнер бота..." $BLUE
    cd deployment
    $DC exec carting-bot bash
    cd ..
}

function shell_api() {
    colored_echo "🐚 Вход в контейнер API..." $BLUE
    cd deployment
    $DC exec carting-api bash
    cd ..
}

function clean_bot() {
    colored_echo "⚠️  Удаление всех данных и контейнеров..." $YELLOW
    read -p "Вы уверены? Все данные будут удалены! (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd deployment
        $DC down -v --remove-orphans
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
        local backup_file="backups/races_backup_$(date -u +%Y%m%dT%H%M%SZ).db"
        local temporary_backup="$backup_file.tmp"
        mkdir -p backups
        umask 077
        if ! python3 - "data/races.db" "$temporary_backup" <<'PY'
import sqlite3
import sys

source = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
destination = sqlite3.connect(sys.argv[2])
try:
    source.backup(destination)
    result = destination.execute("PRAGMA integrity_check").fetchone()[0]
    if result != "ok":
        raise RuntimeError(f"SQLite integrity_check failed: {result}")
finally:
    destination.close()
    source.close()
PY
        then
            rm -f "$temporary_backup"
            colored_echo "❌ Не удалось создать проверенный бэкап базы данных!" $RED
            return 1
        fi
        mv "$temporary_backup" "$backup_file"
        colored_echo "✅ Резервная копия создана: $backup_file" $GREEN
    else
        colored_echo "❌ База данных не найдена!" $RED
    fi
}

function clear_database() {
    colored_echo "🗑️  Очистка базы данных..." $BLUE
    cd deployment
    $DC exec carting-bot python bot/utils/clear_database.py
    cd ..
}

function health_check() {
    colored_echo "🏥 Проверка здоровья системы..." $BLUE
    cd deployment
    $DC exec carting-bot python bot/utils/health_check.py
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
    full-update)
        full_update
        ;;
    shell)
        shell_bot
        ;;
    shell-api)
        shell_api
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

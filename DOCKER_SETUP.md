# Docker Setup для CartingBot

## Проблемы и решения

### Проблема: "attempt to write a readonly database"

**Причина:** Неправильные права доступа к папке базы данных в Docker контейнере

**Решение:**

1. **Остановить контейнер:**
   ```bash
   docker-compose down
   ```

2. **Инициализировать папки с правильными правами:**
   ```bash
   # Автоматически
   ./scripts/manage.sh start
   
   # Или вручную
   ./scripts/init_docker_dirs.sh
   ```

3. **Пересобрать и запустить контейнер:**
   ```bash
   docker-compose up -d --build
   ```

### Проблема: "Не найден файл config/config.py"

**Причина:** Отсутствует файл `config/__init__.py` или неправильно настроен `config/config.py`

**Решение:**

1. **Создать необходимые файлы:**
   ```bash
   # Создать config/__init__.py
   echo "# Config package for CartingBot" > config/__init__.py
   
   # Создать config/config.py из примера
   cp config/config.py.example config/config.py
   
   # Создать .env файл
   cp env.example .env
   ```

2. **Настроить .env файл:**
   ```bash
   # Отредактировать .env файл
   nano .env
   ```
   
   Заменить `YOUR_BOT_TOKEN_HERE` на реальный токен бота.

3. **Пересобрать Docker образ:**
   ```bash
   # Остановить контейнер
   docker-compose down
   
   # Пересобрать образ
   docker-compose build --no-cache
   
   # Запустить заново
   docker-compose up -d
   ```

### Пути в Docker контейнере:

- **Рабочая директория:** `/app`
- **База данных:** `/app/data/races.db`
- **Логи:** `/app/logs/bot.log`
- **Конфигурация:** `/app/config/config.py`
- **Переменные окружения:** передаются через docker-compose.yml

### Структура файлов:

```
CartingBotPython/
├── .env                    # Переменные окружения (создать из env.example)
├── docker-compose.yml      # Docker Compose конфигурация
├── config/
│   ├── __init__.py         # Пакет конфигурации (создать!)
│   ├── config.py           # Основной конфиг (создать из примера)
│   └── config.py.example   # Пример конфигурации
└── docker/
    └── Dockerfile          # Docker образ
```

### Быстрое исправление:

```bash
# Использовать скрипт исправления
./scripts/fix_config.sh

# Или через manage.sh
./scripts/manage.sh fix-config
```

### Проверка:

```bash
# Проверить что файлы созданы
ls -la config/
ls -la .env

# Проверить логи контейнера
docker-compose logs carting-bot

# Проверить статус
docker-compose ps
```

### Переменные окружения:

Docker Compose автоматически читает `.env` файл и передает переменные в контейнер:

```env
BOT_TOKEN=ваш_токен_бота
DATABASE_PATH=/app/data/races.db
LOG_FILE=/app/logs/bot.log
LOG_LEVEL=INFO
PARSER_TIMEOUT=30
PARSER_MAX_RETRIES=3
MAX_COMPETITORS_PER_PAGE=10
ENABLE_WEBHOOKS=false
WEBHOOK_URL=
WEBHOOK_PORT=8443
```

## Новые возможности

### Автоматическая инициализация

Теперь скрипт `manage.sh` автоматически:
- Создает папки `data/` и `logs/` с правильными правами доступа
- Проверяет конфигурацию при запуске
- Инициализирует базу данных

### Entrypoint скрипт

Docker контейнер теперь использует `entrypoint.sh` который:
- Проверяет права доступа к папкам
- Создает конфигурационные файлы если отсутствуют
- Валидирует переменные окружения
- Выводит диагностическую информацию

### Дополнительные скрипты

- `scripts/init_docker_dirs.sh` - инициализация прав доступа к папкам
- `scripts/test_database.py` - тестирование базы данных
- `scripts/manage.sh test-db` - команда для тестирования БД 
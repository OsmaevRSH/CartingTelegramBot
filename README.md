# 🏁 CartingBot Python

Асинхронный Telegram бот для парсинга результатов картинга с сайта mayak.kartchrono.com

Построен на основе официальной библиотеки [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) с полной поддержкой асинхронности.

## ✨ Возможности

- ⚡ **Полная асинхронность** - быстрая обработка запросов
- 📅 **Парсинг архива заездов** по датам
- 🏎️ **Детальные результаты** заездов с временами по секторам
- 📊 **Рейтинг гонщиков** по лучшим кругам
- 🎯 **Персональная статистика** для каждого пользователя
- 📋 **Добавление заездов** с выбором пользователя, даты и карта
- 🔄 **Автоматический перезапуск** через Docker
- 🛡️ **Обработка ошибок** парсинга и сети
- 📝 **Логирование** всех операций

## 🚀 Быстрый старт

Выберите один из способов запуска:

### 🐳 Docker (рекомендуется для сервера)

**Плюсы**: Автоматический перезапуск, изолированная среда, простое развертывание  
**Минусы**: Требует Docker, больше ресурсов

1. **Клонируй репозиторий:**
```bash
git clone <your-repo-url>
cd CartingBotPython
```

2. **Создай файл с переменными окружения:**
```bash
cp env.example .env
```

3. **Отредактируй файл .env и добавь токен бота:**
```bash
nano .env
# Замени YOUR_BOT_TOKEN_HERE на реальный токен
```

4. **Запусти автоматическую установку:**
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### 💻 Локальный запуск (рекомендуется для разработки)

**Плюсы**: Простота, быстрый старт, легкая отладка  
**Минусы**: Нужно настраивать Python окружение, нет автоматического перезапуска

1. **Клонируй репозиторий:**
```bash
git clone <your-repo-url>
cd CartingBotPython
```

2. **Создай файл с переменными окружения:**
```bash
cp env.example .env
nano .env  # Добавь токен бота
```

3. **Запусти бота:**
```bash
./run_bot.sh
```

### Ручная установка (для опытных пользователей)

1. **Клонируй репозиторий:**
```bash
git clone <your-repo-url>
cd CartingBotPython
```

2. **Создай виртуальное окружение:**
```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Установи зависимости:**
```bash
pip install -r requirements.txt
```

4. **Создай файл с переменными окружения:**
```bash
cp env.example .env
nano .env  # Добавь токен бота
```

5. **Создай необходимые директории:**
```bash
mkdir -p data logs
```

6. **Запусти бота:**
```bash
python main.py
```

## 📋 Команды бота

- `/add` - Добавить новый заезд
- `/stats` - Посмотреть свою статистику
- `/best` - Рейтинг лучших гонщиков
- `/best_today` - Рейтинг за сегодня

## 🛠️ Управление

### Локальный запуск

```bash
# Простой запуск (автоматически настраивает все)
./run_bot.sh

# Тестирование настройки перед запуском
python3 scripts/test_local_setup.py

# Тестирование парсеров
python3 scripts/test_bot.py

# Проверка здоровья системы
python3 scripts/health_check.py

# Статистика базы данных
python3 scripts/show_db_stats.py

# Очистка базы данных
python3 scripts/clear_database.py
```

### Управление через Docker

Используй скрипт `scripts/manage.sh` для управления ботом:

```bash
# Сделать скрипт исполняемым
chmod +x scripts/manage.sh

# Запустить бота
./scripts/manage.sh start

# Остановить бота
./scripts/manage.sh stop

# Перезапустить бота
./scripts/manage.sh restart

# Посмотреть статус
./scripts/manage.sh status

# Посмотреть логи
./scripts/manage.sh logs

# Посмотреть логи в реальном времени
./scripts/manage.sh logs-f

# Обновить и перезапустить
./scripts/manage.sh update

# Создать резервную копию базы данных
./scripts/manage.sh backup

# Исправить проблемы с конфигурацией
./scripts/manage.sh fix-config
```

## 📁 Структура проекта

```
CartingBotPython/
├── src/                    # Исходный код
│   ├── bot/               # Основной код бота
│   │   └── bot.py         # Главный файл бота
│   ├── database/          # Работа с базой данных
│   │   └── db.py          # Функции для работы с SQLite
│   ├── models/            # Модели данных
│   │   └── models.py      # Dataclasses для структур данных
│   └── parsers/           # Парсеры веб-страниц
│       └── parsers.py     # Асинхронные парсеры
├── config/                # Конфигурация
│   ├── config.py         # Основной конфиг (создается из .example)
│   └── config.py.example # Пример конфигурации
├── docker/               # Docker файлы
│   └── Dockerfile        # Описание контейнера
├── scripts/              # Скрипты управления
│   ├── deploy.sh         # Автоматическое развертывание
│   └── manage.sh         # Управление ботом
├── data/                 # Данные (создается автоматически)
│   └── races.db          # База данных SQLite
├── logs/                 # Логи (создается автоматически)
│   └── bot.log           # Лог файл
├── main.py               # Точка входа
├── requirements.txt      # Python зависимости
├── docker-compose.yml    # Конфигурация Docker Compose
└── env.example          # Пример переменных окружения
```

## 🔧 Развертывание на сервере

### Ubuntu 20.04 (рекомендуется)

1. **Подключись к серверу:**
```bash
ssh user@your-server-ip
```

2. **Клонируй проект:**
```bash
git clone <your-repo-url>
cd CartingBotPython
```

3. **Создай файл с переменными окружения:**
```bash
cp env.example .env
nano .env
# Заполни BOT_TOKEN и другие настройки
```

4. **Запусти автоматическую установку:**
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

Скрипт автоматически:
- Установит Docker и Docker Compose
- Создаст необходимые директории
- Соберет и запустит контейнеры
- Настроит автоматический перезапуск

### Systemd сервис (альтернатива)

Для еще большей надежности можно создать systemd сервис:

```bash
sudo nano /etc/systemd/system/carting-bot.service
```

```ini
[Unit]
Description=CartingBot Docker Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/CartingBotPython
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Затем активируй сервис:
```bash
sudo systemctl daemon-reload
sudo systemctl enable carting-bot.service
sudo systemctl start carting-bot.service
```

## 🔧 Конфигурация

Основные настройки можно изменить в файле `.env`:

```env
# Токен Telegram бота
BOT_TOKEN=your_bot_token_here

# Настройки логирования
LOG_LEVEL=INFO

# Настройки парсера
PARSER_TIMEOUT=30
PARSER_MAX_RETRIES=3

# Настройки бота
MAX_COMPETITORS_PER_PAGE=10
```

## 🏥 Мониторинг и логи

### Просмотр логов:
```bash
# Последние 50 записей
./scripts/manage.sh logs

# В реальном времени
./scripts/manage.sh logs-f

# Или через Docker напрямую
docker-compose logs -f carting-bot
```

### Проверка статуса:
```bash
./scripts/manage.sh status
```

### Healthcheck:
Docker Compose автоматически проверяет здоровье контейнера каждые 30 секунд.

## 📊 База данных

Бот использует SQLite базу данных, которая автоматически создается в `data/races.db`.

### Резервные копии:
```bash
# Создать резервную копию
./scripts/manage.sh backup

# Или вручную
cp data/races.db backups/races_backup_$(date +%Y%m%d_%H%M%S).db
```

## 🛡️ Безопасность

- Контейнер запускается от непривилегированного пользователя
- Данные хранятся в отдельных volume
- Логи ротируются автоматически
- Используются официальные Docker образы

## 🔄 Обновление

Для обновления бота до новой версии:

```bash
# Остановить текущую версию
./scripts/manage.sh stop

# Обновить код
git pull

# Пересобрать и запустить
./scripts/manage.sh update
```

## 🐛 Устранение проблем

### Бот не запускается:
1. Проверь токен в `.env` файле
2. Убедись, что Docker запущен: `sudo systemctl status docker`
3. Проверь логи: `./scripts/manage.sh logs`

### Ошибка "Создайте config.py":
```bash
# Быстрое исправление
./scripts/manage.sh fix-config

# Или вручную
cp config/config.py.example config/config.py
./scripts/manage.sh update
```

### Ошибки парсинга:
1. Проверь доступность сайта mayak.kartchrono.com
2. Увеличь PARSER_TIMEOUT в `.env`
3. Проверь логи на детали ошибок

### Проблемы с базой данных:
1. Проверь права доступа к директории `data/`
2. Создай резервную копию и пересоздай базу
3. Проверь свободное место на диске

## 📝 Лицензия

MIT License - смотри файл LICENSE

## 🤝 Вклад в проект

1. Сделай Fork проекта
2. Создай feature branch (`git checkout -b feature/amazing-feature`)
3. Закоммить изменения (`git commit -m 'Add some amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Открой Pull Request

## 📞 Поддержка

Если у тебя возникли проблемы:
1. Проверь логи: `./scripts/manage.sh logs`
2. Создай issue в GitHub
3. Опиши проблему максимально подробно 
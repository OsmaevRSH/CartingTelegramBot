# 📖 Примеры использования CartingBot

## Локальный запуск

### Первый запуск
```bash
# Клонируем проект
git clone https://github.com/your-username/CartingBotPython.git
cd CartingBotPython

# Создаем и настраиваем .env
cp env.example .env
nano .env  # Добавляем токен бота

# Запускаем
./run_bot.sh
```

### Повторный запуск
```bash
# Просто запускаем
./run_bot.sh
```

### Тестирование
```bash
# Проверяем настройки
python3 scripts/test_local_setup.py

# Тестируем парсеры
python3 scripts/test_bot.py

# Проверяем здоровье
python3 scripts/health_check.py
```

## Запуск через Docker

### Первый запуск
```bash
# Клонируем проект
git clone https://github.com/your-username/CartingBotPython.git
cd CartingBotPython

# Создаем и настраиваем .env
cp env.example .env
nano .env  # Добавляем токен бота

# Автоматический деплой
./scripts/deploy.sh
```

### Управление
```bash
# Статус
./scripts/manage.sh status

# Логи
./scripts/manage.sh logs

# Логи в реальном времени
./scripts/manage.sh logs-f

# Перезапуск
./scripts/manage.sh restart

# Остановка
./scripts/manage.sh stop

# Бэкап
./scripts/manage.sh backup
```

## Работа с базой данных

### Просмотр статистики
```bash
python3 scripts/show_db_stats.py
```

Пример вывода:
```
📊 Статистика базы данных бота
===================================
📁 Файл базы данных: data/races.db
📦 Размер файла: 45.3 KB

📈 ОБЩАЯ СТАТИСТИКА:
   🏁 Всего заездов: 125
   👥 Уникальных пользователей: 8
   📅 Дней с заездами: 15

🏆 ТОП ПОЛЬЗОВАТЕЛЕЙ:
    1. ID:123456789 - 45 заездов
    2. ID:987654321 - 32 заезда
    3. ID:456789123 - 28 заездов
```

### Очистка базы данных
```bash
# Интерактивная очистка с подтверждением
python3 scripts/clear_database.py

# Принудительная очистка (без подтверждения)
python3 scripts/clear_database_force.py
```

## Примеры настройки .env

### Минимальная настройка
```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

### Полная настройка
```env
# Токен бота
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Настройки логирования
LOG_LEVEL=INFO

# Настройки парсера
PARSER_TIMEOUT=30
PARSER_MAX_RETRIES=3

# Настройки бота
MAX_COMPETITORS_PER_PAGE=10
```

## Команды бота в Telegram

### Основные команды
- `/add` - Добавить заезд
- `/stats` - Моя статистика
- `/best` - Общий рейтинг
- `/best_today` - Рейтинг за сегодня

### Примеры использования

1. **Добавление заезда**:
   - Отправляем `/add`
   - Выбираем пользователя
   - Выбираем дату заезда
   - Выбираем конкретный заезд
   - Выбираем номер карта

2. **Просмотр статистики**:
   - Отправляем `/stats`
   - Бот показывает все заезды пользователя
   - Можно посмотреть детали каждого заезда

3. **Рейтинг**:
   - `/best` - показывает лучших гонщиков по лучшему кругу
   - `/best_today` - показывает лучших за сегодня

## Мониторинг и отладка

### Просмотр логов (локально)
```bash
# Последние записи
tail -f logs/bot.log

# Поиск ошибок
grep "ERROR" logs/bot.log

# Поиск конкретного пользователя
grep "user_id: 123456789" logs/bot.log
```

### Просмотр логов (Docker)
```bash
# Последние записи
./scripts/manage.sh logs

# В реальном времени
./scripts/manage.sh logs-f
```

### Проверка здоровья
```bash
# Полная проверка
python3 scripts/health_check.py
```

Пример вывода:
```
🏥 Проверка здоровья CartingBot...
==================================================
🌐 Проверка доступности сайта...
   ✅ Сайт доступен
   
🔍 Проверка парсера...
   ✅ Парсер работает (23 дня)
   
🗄️ Проверка базы данных...
   ✅ База данных работает (125 записей)
   
📝 Проверка лог файла...
   ✅ Лог файл актуален
   
==================================================
✅ Все проверки пройдены успешно!
```

## Резервное копирование

### Создание бэкапа
```bash
# Через Docker
./scripts/manage.sh backup

# Локально
mkdir -p backups
cp data/races.db backups/races_backup_$(date +%Y%m%d_%H%M%S).db
```

### Восстановление из бэкапа
```bash
# Остановить бота
./scripts/manage.sh stop  # Docker
# или Ctrl+C для локального

# Восстановить базу
cp backups/races_backup_20240101_120000.db data/races.db

# Запустить бота
./scripts/manage.sh start  # Docker
./run_bot.sh                # Локально
```

## Troubleshooting

### Проблема: Токен не работает
```bash
# Проверить .env файл
cat .env | grep BOT_TOKEN

# Проверить через BotFather
# Отправить /mybots в @BotFather
```

### Проблема: Парсер не работает
```bash
# Проверить доступность сайта
curl -I https://mayak.kartchrono.com/archive/

# Тестировать парсер
python3 scripts/test_bot.py
```

### Проблема: База данных заблокирована
```bash
# Остановить все процессы
./scripts/manage.sh stop

# Проверить файл базы
ls -la data/races.db

# Перезапустить
./scripts/manage.sh start
```

---

💡 **Совет**: Регулярно делайте бэкапы базы данных и следите за логами для раннего обнаружения проблем. 
# 🏁 Carting Bot Python

Асинхронный Telegram бот для парсинга результатов картинга с сайта mayak.kartchrono.com

Построен на основе официальной библиотеки [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) с полной поддержкой асинхронности.

## Установка

1. Клонируй репозиторий:
```bash
git clone <your-repo-url>
cd CartingBotPython
```

2. Создай виртуальное окружение:
```bash
python3 -m venv venv
source venv/bin/activate  # для macOS/Linux
# или
venv\Scripts\activate  # для Windows
```

3. Установи зависимости:
```bash
pip install -r requirements.txt
```

4. Создай файл `config.py` и добавь токен бота:
```python
BOT_TOKEN = "your_telegram_bot_token_here"
```

5. Запусти бота:
```bash
python bot.py
```

## Команды бота

- `/start` - начать работу с ботом
- `/ping` - проверка работы бота
- `/archive` - получить архив заездов
- `/help` - показать справку

## Структура проекта

- `bot.py` - основной файл бота (асинхронный)
- `models.py` - модели данных (dataclasses)
- `parsers.py` - асинхронные парсеры для извлечения данных с сайта
- `requirements.txt` - зависимости проекта
- `config.py.example` - пример конфигурации

## Возможности

- ⚡ **Полная асинхронность** - быстрая обработка запросов
- 📅 **Парсинг архива заездов** по датам
- 🏎️ **Парсинг результатов** конкретных заездов
- 📊 **Извлечение данных** о картах (номер, лучший круг, позиция)
- 🛡️ **Обработка ошибок** парсинга и сети
- 📝 **Логирование** всех операций

## Технологии

- **[python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)** v22.2 - официальная библиотека для Telegram Bot API
- **aiohttp** - асинхронный HTTP клиент для парсинга
- **BeautifulSoup4** - парсинг HTML
- **Python 3.9+** с полной поддержкой asyncio

## TODO

- [ ] Добавить команду для получения результатов конкретного заезда
- [ ] Добавить кэширование результатов 
- [ ] Добавить фильтрацию по дате
- [ ] Добавить webhook для продакшена
- [ ] Добавить inline кнопки для навигации по архиву
- [ ] Добавить экспорт результатов в CSV/Excel 
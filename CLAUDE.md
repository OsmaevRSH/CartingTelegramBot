# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CartingBot** — Telegram-бот для отслеживания результатов гонок на картах. Скрейпит данные с сайта kartchrono и хранит статистику заездов в SQLite.

## Commands

### Local development (venv)
```bash
./manage_local.sh start        # Запустить бота локально
./manage_local.sh health       # Проверить работоспособность
./manage_local.sh clear-db     # Очистить базу данных
./manage_local.sh check-perm   # Проверить права на файлы
```

### Remote deployment (Docker)
```bash
./manage_remote.sh start       # Запустить в Docker
./manage_remote.sh stop        # Остановить
./manage_remote.sh restart     # Перезапустить
./manage_remote.sh logs-f      # Стриминг логов
./manage_remote.sh update      # Обновить и перезапустить
./manage_remote.sh shell       # Войти в контейнер
./manage_remote.sh backup      # Бэкап базы данных
```

### Health check
```bash
python3 utils/health_check.py  # Проверяет сайт, парсеры, БД, лог-файл
```

## Architecture

```
main.py                        # Точка входа → src.bot.bot.main()
src/
  bot/bot.py                   # Telegram ConversationHandler, команды, колбэки
  parsers/parsers.py            # 3 парсера: ArchiveParser, RaceParser, FullRaceInfoParser
  database/db.py               # SQLite CRUD операции
  models/models.py             # Датаклассы: Race, DayRaces, Cart, Competitor, LapData
config/config.py               # Загрузка .env через python-dotenv
utils/                         # health_check.py, clear_database.py, check_permissions.py
deployment/                    # Dockerfile, docker-compose.yml, entrypoint.sh
```

## Key Data Flow

1. Пользователь вызывает `/add` → `ConversationHandler` управляет диалогом
2. `ArchiveParser` скрейпит даты и ссылки на заезды с kartchrono
3. Пользователь выбирает дату → заезд → карт
4. `RaceParser.parse_with_html()` возвращает `(carts, html)` — HTML кэшируется в `context.user_data`
5. `FullRaceInfoParser.parse(..., html=cached_html)` использует кэш, избегая второго HTTP-запроса
6. `db.py` сохраняет данные участника в SQLite
7. `/stats`, `/best`, `/best_today` — чтение и отображение статистики

## Bot Commands

- `/add` — добавить результат заезда (многошаговый диалог)
- `/cancel` — отменить текущий диалог `/add`
- `/stats` — личная статистика
- `/best` — глобальная таблица лучших кругов
- `/best_today` — таблица лучших за сегодня

## Database Schema (SQLite)

Таблица `user_competitors`, PRIMARY KEY `(user_id, date, race_number, num)`:
- Идентификация: `user_id`, `date` (формат `DD.MM.YYYY`), `race_number`, `race_href`, `competitor_id`
- Результаты: `num` (карт), `name`, `pos`, `laps`, `theor_lap` (мс, int), `best_lap` (строка)
- Форматированные данные: `binary_laps`, `theor_lap_formatted`, `display_name`, `gap_to_leader`
- JSON: `lap_times_json` (время секторов по каждому кругу)

Сортировка дат в SQL: `ORDER BY substr(date,7,4) || substr(date,4,2) || substr(date,1,2) DESC` —
формат `DD.MM.YYYY` нельзя сортировать напрямую, нужно приводить к `YYYYMMDD`.

SQLite запущен с `PRAGMA journal_mode=WAL` для корректной работы при конкурентных запросах.

## Configuration

Копировать `env.example` в `.env`. Ключевые переменные:
- `BOT_TOKEN` — токен Telegram-бота (обязателен; по умолчанию пустая строка — бот не запустится)
- `DATABASE_PATH` — путь к SQLite (по умолчанию `data/races.db`)
- `LOG_FILE` — путь к лог-файлу
- `PARSER_TIMEOUT`, `PARSER_MAX_RETRIES` — настройки скрейпинга
- `MAX_COMPETITORS_PER_PAGE` — пагинация в inline-клавиатурах

## Async Patterns

Все HTTP-запросы используют `aiohttp` с `async/await`. Telegram-хэндлеры — корутины (`async def`).

`RaceParser` предоставляет два метода:
- `parse(href)` → `List[Cart]` — только список картов
- `parse_with_html(href)` → `(List[Cart], html)` — для кэширования HTML между запросами

`FullRaceInfoParser.parse(href, carts, html=None)` — если `html` передан, HTTP-запрос не выполняется.

## ConversationHandler States

Состояния в `bot.py`: `SELECT_USER` → `SELECT_DATE` → `SHOW_RACES` → `SHOW_CARTS`.

Важные инварианты `context.user_data`:
- `today_dr` — объект `DayRaces` для сегодняшней даты (или `None`); кэшируется при выборе пользователя
- `today_exists` — `bool`; используется всеми функциями пагинации дат
- `current_race_html` — сырой HTML страницы заезда; позволяет `FullRaceInfoParser` не делать второй запрос

`fallbacks` включает `/cancel` — сбрасывает `user_data` и завершает диалог.

## Key Helpers in bot.py

- `_format_competitor_info(comp_data: tuple) -> str` — форматирует строку заезда для показа
- `_render_leaderboard(context, chat_id, competitors, title) -> str` — рендерит таблицу лидеров
- `_delete_command_message(update, context)` — удаляет команду пользователя из чата (или ставит реакцию если нет прав)
- `_build_keyboard(rows)` — строит `InlineKeyboardMarkup` из списка строк `[(text, callback_data)]`

## Formatting

Все сообщения с форматированием используют `ParseMode.HTML`. Пользовательские строки (имена из Telegram, данные из kartchrono) экранируются через `html.escape()` перед подстановкой. Жирный текст: `<b>...</b>`, таблицы: `<pre>...</pre>`.

## Database: best_lap_ms

Колонка `best_lap_ms INTEGER` хранит время лучшего круга в миллисекундах для SQL-сортировки. Заполняется при `save_competitor()`. При запуске `init_db()` автоматически мигрирует существующие строки. `get_best_competitors()` и `get_best_competitors_today()` используют CTE с `GROUP BY user_id` — один лучший результат на пользователя, сортировка в SQL.

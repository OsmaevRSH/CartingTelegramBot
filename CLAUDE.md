# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Важно:** при любых изменениях в проекте — обновляй этот файл, чтобы он всегда отражал актуальное состояние.

## Project Overview

**CartingBot** — монорепо с тремя независимыми сервисами:
1. **bot/** — Telegram-бот для отслеживания результатов картинга
2. **api/** — FastAPI бэкенд, предоставляющий REST API для WebApp
3. **webapp/** — Telegram Mini App (React + Vite + Tailwind)

Общая бизнес-логика (парсеры, БД, модели, конфиг) вынесена в **core/**.

## Top-level Structure

```
carting/
├── core/               ← Общий код (parsers, db, models, config)
├── bot/                ← Telegram бот
├── api/                ← FastAPI REST API
├── webapp/             ← React Telegram Mini App
├── deployment/         ← Docker, docker-compose, nginx
├── manage_local.sh     ← Локальный запуск (venv)
└── manage_remote.sh    ← Удалённый запуск (Docker)
```

## Commands

### Local development (venv)
```bash
./manage_local.sh start        # Запустить бота
./manage_local.sh api          # Запустить FastAPI на :8000
./manage_local.sh webapp       # Запустить React dev-server на :5173
./manage_local.sh health       # Проверить работоспособность
./manage_local.sh clear-db     # Очистить базу данных
```

### Remote deployment (Docker)
```bash
./manage_remote.sh start       # Запустить все сервисы (bot + api + webapp)
./manage_remote.sh stop        # Остановить
./manage_remote.sh restart     # Перезапустить
./manage_remote.sh logs-f      # Стриминг логов
./manage_remote.sh update      # Обновить и перезапустить
./manage_remote.sh shell       # Войти в контейнер бота
./manage_remote.sh shell-api   # Войти в контейнер API
./manage_remote.sh backup      # Бэкап базы данных
./manage_remote.sh full-update # Проверенный бэкап, Git pull и полное пересоздание сервисов
```

## Architecture

```
core/
  config/config.py             # Загрузка .env, ROOT_DIR = core/config → core → project root
  models/models.py             # Датаклассы: Race, DayRaces, Cart, Competitor, LapData
  parsers/parsers.py           # ArchiveParser, RaceParser, FullRaceInfoParser
  database/db.py               # SQLite CRUD операции

bot/
  main.py                      # Точка входа → bot.handlers.bot.main()
  handlers/bot.py              # Telegram ConversationHandler, команды, колбэки
  utils/
    health_check.py            # Проверка сайта, парсеров, БД, лог-файла
    clear_database.py          # Очистка БД с подтверждением

api/
  main.py                      # FastAPI app, startup → init_db(), CORS
  routes/
    auth.py                    # Telegram Login start/callback/exchange, refresh, logout
    archive.py                 # GET /api/archive
    races.py                   # GET /api/races?href=, GET /api/races/full?href=
    stats.py                   # GET/POST/DELETE /api/stats/...
    leaderboard.py             # GET /api/leaderboard, /api/leaderboard/today

webapp/
  src/
    App.jsx                    # Root: 3 tabs (add/stats/leaderboard)
    hooks/useTelegram.js       # Telegram WebApp SDK интеграция
    api/client.js              # fetch-обёртки для всех API эндпоинтов
    components/
      BottomNav.jsx            # Нижняя навигация (3 таба)
      RaceCard.jsx             # Карточка заезда с expand + delete
      LapTimesTable.jsx        # Таблица кругов (#, Время, S1-S4)
      LoadingSpinner.jsx       # Спиннер с label
    pages/
      AddRace.jsx              # 4-шаговый wizard: дата → заезд → карт → результат
      MyStats.jsx              # Список заездов пользователя
      Leaderboard.jsx          # Рейтинг (все времена / сегодня) с подиумом

deployment/
  bot/Dockerfile               # Python 3.11, копирует core/ + bot/
  api/Dockerfile               # Python 3.11, копирует core/ + api/
  webapp/Dockerfile            # Multi-stage: Node build → nginx serve
  webapp/nginx.conf            # SPA fallback + proxy /api/ → carting-api:8000
  docker-compose.yml           # 3 сервиса: carting-bot, carting-api, carting-webapp
```

## Key Data Flow

### Bot
1. Пользователь вызывает `/add` → `ConversationHandler` управляет диалогом
2. `ArchiveParser` скрейпит даты и ссылки на заезды с kartchrono
3. Пользователь выбирает дату → заезд → карт
4. `RaceParser.parse_with_html()` возвращает `(carts, html)` — HTML кэшируется в `context.user_data`
5. `FullRaceInfoParser.parse(..., html=cached_html)` использует кэш, избегая второго HTTP-запроса
6. `db.save_competitor()` сохраняет данные в SQLite

### WebApp
1. Пользователь открывает Mini App через Telegram → `useTelegram()` получает `userId`
2. Wizard в `AddRace.jsx`: fetch archive → fetch carts → fetch full race → POST /api/stats
3. `MyStats.jsx`: GET /api/stats/{userId} → список карточек с lap times
4. `Leaderboard.jsx`: GET /api/leaderboard или /api/leaderboard/today → подиум + список

## Bot Commands

- `/add` — добавить результат заезда (многошаговый диалог)
- `/stats` — статистика пользователей; поддерживает возврат к выбору пользователя кнопкой
- `/best` — глобальная таблица лучших кругов
- `/best_today` — таблица лучших за сегодня
- `/cancel` — отменить текущий диалог `/add` (скрыта из меню)

## API Endpoints

| Метод | Путь | Описание |
|-------|------|---------|
| GET | /api/archive | Список дней с заездами из kartchrono |
| GET | /api/races?href= | Список картов для заезда |
| GET | /api/races/full?href= | Полная информация о заезде с кругами |
| GET | /api/stats/{user_id} | Заезды пользователя |
| POST | /api/stats | Сохранить заезд |
| DELETE | /api/stats/{user_id}/{date}/{race_number}/{num} | Удалить заезд |
| GET | /api/leaderboard | Топ всех времён |
| GET | /api/leaderboard/today?date= | Топ за день |
| GET | /api/health | Health check |
| POST | /api/mobile/auth/telegram/start | Начать Telegram Login с PKCE |
| GET | /api/mobile/auth/telegram/login | Фиксированная HTTPS-страница Telegram Login |
| POST | /api/mobile/auth/telegram/callback | Проверить Telegram payload и перенаправить в `carting://auth/callback` |
| POST | /api/mobile/auth/telegram/exchange | Обмен authorization code + PKCE verifier на access/refresh tokens |
| POST | /api/mobile/auth/refresh | Ротация refresh session и выдача новой пары токенов |
| POST | /api/mobile/auth/logout | Отзыв refresh session |
| GET | /api/mobile/stats | Заезды владельца bearer-токена |
| POST | /api/mobile/stats | Сохранить заезд владельцу bearer-токена |
| DELETE | /api/mobile/stats/{date}/{race_number}/{num} | Удалить свой заезд |

## Database Schema (SQLite)

Таблица `user_competitors`, PRIMARY KEY `(user_id, date, race_number, num)`:
- Идентификация: `user_id`, `date` (формат `DD.MM.YYYY`), `race_number`, `race_href`, `competitor_id`
- Результаты: `num` (карт), `name`, `pos`, `laps`, `theor_lap` (мс, int), `best_lap` (строка)
- Форматированные данные: `binary_laps`, `theor_lap_formatted`, `display_name`, `gap_to_leader`
- JSON: `lap_times_json` (время секторов по каждому кругу)
- Сортировка: `best_lap_ms INTEGER` для SQL-сортировки

Сортировка дат в SQL: `ORDER BY substr(date,7,4) || substr(date,4,2) || substr(date,1,2) DESC`

SQLite запущен с `PRAGMA journal_mode=WAL` для корректной работы при конкурентных запросах.

Для Telegram Login `init_db()` также создаёт три таблицы:

- `mobile_telegram_login_transactions` — краткоживущие PKCE-транзакции Telegram Login; в базе хранится SHA-256 хеш `state` и challenge.
- `mobile_telegram_authorization_codes` — одноразовые authorization code, связанные с завершённой транзакцией; в базе хранится только SHA-256 хеш кода.
- `mobile_refresh_sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires_at TEXT NOT NULL, revoked_at TEXT)` — refresh-сессии. В базе хранится только SHA-256 хеш токена; `rotate_refresh_session()` атомарно отзывает предшественник и создаёт replacement-токен, а `revoke_refresh_session()` отзывает активную сессию.

Время хранения и статусы используют timezone-aware UTC ISO-8601 timestamps. Генерируемые коды и токены создаются через `secrets.token_urlsafe`; исходные значения никогда не сохраняются.

## Configuration

Единственный `.env` файл находится в корне проекта.

- `BOT_TOKEN` — секретный токен Telegram-бота, обязательный для проверки Login payload; не хранить в репозитории
- `TELEGRAM_LOGIN_BOT_USERNAME` — username бота без `@`, настроенного для Telegram Login
- `TELEGRAM_LOGIN_ORIGIN` — публичный HTTPS origin login-домена без path, query и fragment, например `https://carting.example.com`
- `AUTH_SECRET` — длинный случайный секрет для подписи mobile-auth access tokens; не хранить в репозитории
- Access token всегда имеет фиксированный срок `900` секунд (не переопределяется окружением)
- `REFRESH_TOKEN_TTL_SECONDS` — срок refresh session, по умолчанию `2592000` секунд
- `DATABASE_PATH` — путь к SQLite (по умолчанию `data/races.db`)
- `LOG_FILE` — путь к лог-файлу
- `PARSER_TIMEOUT`, `PARSER_MAX_RETRIES` — настройки скрейпинга
- `MAX_COMPETITORS_PER_PAGE` — пагинация в inline-клавиатурах
- `API_HOST`, `API_PORT` — настройки FastAPI (по умолчанию 0.0.0.0:8000)

Docker переопределяет `DATABASE_PATH` и `LOG_FILE` под пути внутри контейнеров.
Webapp использует переменную сборки `VITE_API_URL` (см. `webapp/.env.example`).

Нативное iOS-приложение начинает вход через `POST /api/mobile/auth/telegram/start` с S256 PKCE challenge и открывает возвращённый URL на настроенном HTTPS login-домене. Сервер принимает Telegram payload только на фиксированном `POST /api/mobile/auth/telegram/callback`, затем перенаправляет приложение на фиксированный `carting://auth/callback` с короткоживущим authorization code и state. Приложение завершает вход только через `POST /api/mobile/auth/telegram/exchange` с исходным PKCE verifier; произвольные redirect URL не поддерживаются.

В production login-домен и reverse proxy должны быть доступны по HTTPS, а `BOT_TOKEN` и `AUTH_SECRET` — заданы секретами окружения. Не логируйте `state`, authorization code, access token или refresh token; TLS должен завершаться только на доверенном proxy. Перед развёртыванием проверьте username бота и origin, а после смены домена или токена перезапустите сервис.

Проверка mobile API и полного проекта:
```bash
/usr/bin/python3 -m pytest tests/test_mobile_stats.py tests/test_mobile_auth.py -q
/usr/bin/python3 -m pytest -q
```

## Imports & Python Path

Все Python-модули используют абсолютные импорты от корня проекта:
- `from core.parsers.parsers import ArchiveParser`
- `from core.database.db import init_db`
- `from core.config.config import BOT_TOKEN`

`bot/main.py` добавляет `os.path.dirname(os.path.dirname(__file__))` (= корень проекта) в `sys.path`.
`bot/utils/*.py` добавляют три уровня вверх по той же логике.
`api/main.py` делает то же самое.

## Async Patterns

Все HTTP-запросы используют `aiohttp`. Telegram-хэндлеры — корутины. FastAPI роуты — `async def`.

## ConversationHandler States

`SELECT_USER` → `SELECT_DATE` → `SHOW_RACES` → `SHOW_CARTS`

Ключевые инварианты `context.user_data`:
- `today_dr` — объект `DayRaces` для сегодня (или None)
- `today_exists` — bool
- `current_race_html` — кэшированный HTML заезда

## Database: best_lap_ms

Колонка `best_lap_ms INTEGER` хранит время лучшего круга в мс для SQL-сортировки. При запуске `init_db()` автоматически мигрирует существующие строки. `get_best_competitors()` и `get_best_competitors_today()` используют CTE с `GROUP BY user_id`.

## Formatting (Bot)

Все сообщения с форматированием используют `ParseMode.HTML`. Пользовательские строки экранируются через `html.escape()`. Жирный текст: `<b>...</b>`, таблицы: `<pre>...</pre>`.

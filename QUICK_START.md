# ⚡ Быстрый старт CartingBot

## Локальный запуск (за 3 шага)

### 1. Клонирование
```bash
git clone <your-repo-url>
cd CartingBotPython
```

### 2. Настройка токена
```bash
cp env.example .env
nano .env  # Замени YOUR_BOT_TOKEN_HERE на реальный токен
```

### 3. Запуск
```bash
./run_bot.sh
```

**Готово!** Бот запущен. Для остановки нажмите `Ctrl+C`.

## Что делает run_bot.sh:

- ✅ Создает виртуальное окружение Python
- ✅ Устанавливает все зависимости
- ✅ Проверяет конфигурацию
- ✅ Создает необходимые директории
- ✅ Тестирует подключение к сайту
- ✅ Запускает бота

## Полезные команды:

```bash
# Тестирование перед запуском
python3 scripts/test_local_setup.py

# Проверка здоровья системы
python3 scripts/health_check.py

# Статистика базы данных
python3 scripts/show_db_stats.py

# Очистка базы данных
python3 scripts/clear_database.py
```

## Требования:

- Python 3.9+
- Токен Telegram бота
- Интернет соединение

## Проблемы?

1. **Нет токена**: Создайте бота через [@BotFather](https://t.me/BotFather)
2. **Ошибка Python**: Убедитесь что установлен Python 3.9+
3. **Проблемы с сайтом**: Проверьте доступность mayak.kartchrono.com
4. **Другие проблемы**: Смотрите полный README.md

---

💡 **Совет**: Для продакшена используйте Docker (смотрите README.md) 
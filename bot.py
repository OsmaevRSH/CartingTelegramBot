import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from parsers import ArchiveParser, RaceParser
from models import ParsingError

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

try:
    from config import BOT_TOKEN
except ImportError:
    print("❌ Не найден файл config.py!")
    print("Создай файл config.py на основе config.py.example")
    exit(1)

# Инициализируем парсеры
archive_parser = ArchiveParser()
race_parser = RaceParser()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    await update.message.reply_text(
        "Привет! Я бот для парсинга результатов картинга.\n"
        "Команды:\n"
        "/ping - проверка работы\n"
        "/archive - получить архив заездов\n"
        "/help - помощь"
    )


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /ping"""
    await update.message.reply_text("pong")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    help_text = """
🏁 Бот для парсинга результатов картинга

Команды:
/start - начать работу
/ping - проверка работы
/archive - получить архив заездов
/help - показать эту помощь

Бот парсит данные с сайта mayak.kartchrono.com
    """
    await update.message.reply_text(help_text)


async def archive_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /archive"""
    try:
        await update.message.reply_text("🔄 Парсю архив заездов...")
        
        day_races = await archive_parser.parse()
        
        if not day_races:
            await update.message.reply_text("❌ Архив пуст")
            return
        
        response = "📅 Архив заездов:\n\n"
        for day_race in day_races[:5]:  # Показываем только первые 5 дат
            date_str = day_race.date.strftime("%d.%m.%Y")
            response += f"📅 {date_str}\n"
            
            for race in day_race.races[:3]:  # Показываем только первые 3 заезда
                response += f"  🏎️ Заезд {race.number}\n"
            
            if len(day_race.races) > 3:
                response += f"  ... и еще {len(day_race.races) - 3} заездов\n"
            
            response += "\n"
        
        if len(day_races) > 5:
            response += f"... и еще {len(day_races) - 5} дат"
        
        await update.message.reply_text(response)
        
    except ParsingError as e:
        await update.message.reply_text(f"❌ Ошибка парсинга: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        await update.message.reply_text(f"❌ Неожиданная ошибка: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик всех остальных сообщений"""
    await update.message.reply_text(
        "Я не понимаю эту команду. Используй /help для получения списка команд."
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)


def main() -> None:
    """Главная функция для запуска бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("archive", archive_command))

    # Обработчик для всех остальных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Обработчик ошибок
    application.add_error_handler(error_handler)

    # Запускаем бота
    print("🚀 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main() 
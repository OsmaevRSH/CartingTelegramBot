import telebot
from telebot import types
from parsers import ArchiveParser, RaceParser
from models import ParsingError

try:
    from config import BOT_TOKEN
except ImportError:
    print("❌ Не найден файл config.py!")
    print("Создай файл config.py на основе config.py.example")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# Инициализируем парсеры
archive_parser = ArchiveParser()
race_parser = RaceParser()


@bot.message_handler(commands=['start'])
def handle_start(message):
    """Обработчик команды /start"""
    bot.reply_to(message, "Привет! Я бот для парсинга результатов картинга.\n"
                         "Команды:\n"
                         "/ping - проверка работы\n"
                         "/archive - получить архив заездов\n"
                         "/help - помощь")


@bot.message_handler(commands=['ping'])
def handle_ping(message):
    """Обработчик команды /ping"""
    bot.reply_to(message, "pong")


@bot.message_handler(commands=['help'])
def handle_help(message):
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
    bot.reply_to(message, help_text)


@bot.message_handler(commands=['archive'])
def handle_archive(message):
    """Обработчик команды /archive"""
    try:
        bot.reply_to(message, "🔄 Парсю архив заездов...")
        
        day_races = archive_parser.parse()
        
        if not day_races:
            bot.reply_to(message, "❌ Архив пуст")
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
        
        bot.reply_to(message, response)
        
    except ParsingError as e:
        bot.reply_to(message, f"❌ Ошибка парсинга: {e}")
    except Exception as e:
        bot.reply_to(message, f"❌ Неожиданная ошибка: {e}")


@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Обработчик всех остальных сообщений"""
    bot.reply_to(message, "Я не понимаю эту команду. Используй /help для получения списка команд.")


if __name__ == "__main__":
    print("🚀 Бот запущен!")
    bot.polling(none_stop=True) 
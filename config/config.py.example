import os
from pathlib import Path

# Получаем корневую директорию проекта
ROOT_DIR = Path(__file__).parent.parent

# Пытаемся загрузить .env файл
try:
    from dotenv import load_dotenv
    env_file = ROOT_DIR / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    # python-dotenv не установлен, используем только переменные окружения
    pass

# Токен Telegram бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Настройки базы данных
DATABASE_PATH = os.getenv("DATABASE_PATH", str(ROOT_DIR / "data" / "races.db"))

# Настройки логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(ROOT_DIR / "logs" / "bot.log"))

# Настройки парсера
PARSER_TIMEOUT = int(os.getenv("PARSER_TIMEOUT", "30"))
PARSER_MAX_RETRIES = int(os.getenv("PARSER_MAX_RETRIES", "3"))

# Настройки бота
MAX_COMPETITORS_PER_PAGE = int(os.getenv("MAX_COMPETITORS_PER_PAGE", "10"))
ENABLE_WEBHOOKS = os.getenv("ENABLE_WEBHOOKS", "False").lower() == "true"
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8443"))

# Создаем директории если их нет
os.makedirs(Path(LOG_FILE).parent, exist_ok=True)
os.makedirs(Path(DATABASE_PATH).parent, exist_ok=True) 
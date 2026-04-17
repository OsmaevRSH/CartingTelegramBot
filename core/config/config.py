import os
from pathlib import Path

# core/config/config.py → core/config → core → project root
ROOT_DIR = Path(__file__).parent.parent.parent

try:
    from dotenv import load_dotenv
    env_file = ROOT_DIR / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

DATABASE_URL = os.getenv("DATABASE_URL", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", str(ROOT_DIR / "data" / "races.db"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(ROOT_DIR / "logs" / "bot.log"))

PARSER_TIMEOUT = int(os.getenv("PARSER_TIMEOUT", "30"))
PARSER_MAX_RETRIES = int(os.getenv("PARSER_MAX_RETRIES", "3"))

MAX_COMPETITORS_PER_PAGE = int(os.getenv("MAX_COMPETITORS_PER_PAGE", "10"))
ENABLE_WEBHOOKS = os.getenv("ENABLE_WEBHOOKS", "False").lower() == "true"
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8443"))

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

os.makedirs(Path(LOG_FILE).parent, exist_ok=True)

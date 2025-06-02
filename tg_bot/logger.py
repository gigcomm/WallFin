import logging
from logging.handlers import RotatingFileHandler

log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler = RotatingFileHandler(
    "bot.log",
    maxBytes=5 * 1024 * 1024,
    backupCount=10
)
handler.setFormatter(log_formatter)

logger = logging.getLogger("aiogram_bot")
logger.setLevel(logging.INFO)
logger.addHandler(handler)
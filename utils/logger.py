"""
Настройка логирования для системы
"""
import os
import sys
from loguru import logger

# Создать директорию для логов
logs_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'logs'
)
os.makedirs(logs_dir, exist_ok=True)

# Настроить логгер
logger.remove()  # Удалить дефолтный handler

# Консольный вывод
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)

# Файловый вывод
logger.add(
    os.path.join(logs_dir, "goszakup_{time:YYYY-MM-DD}.log"),
    rotation="00:00",  # Новый файл каждый день
    retention="30 days",  # Хранить 30 дней
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="DEBUG"
)

# Отдельный файл для ошибок
logger.add(
    os.path.join(logs_dir, "errors_{time:YYYY-MM-DD}.log"),
    rotation="00:00",
    retention="90 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="ERROR"
)

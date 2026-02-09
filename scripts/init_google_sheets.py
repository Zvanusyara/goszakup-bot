"""
Скрипт для инициализации Google Sheets
Создает лист и заголовки в Google таблице
"""
import sys
import os
# Добавить корень проекта в sys.path для импортов
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.google_sheets import get_sheets_manager
from utils.logger import logger

def main():
    """Инициализация Google Sheets"""
    logger.info("=" * 60)
    logger.info("🚀 Инициализация Google Sheets")
    logger.info("=" * 60)

    try:
        # Получить менеджер (это автоматически создаст лист и заголовки)
        sheets_manager = get_sheets_manager()

        if sheets_manager.enabled:
            logger.success("✅ Google Sheets успешно инициализирован!")
            logger.info(f"📊 Таблица: {sheets_manager.spreadsheet.title}")
            logger.info(f"📄 Лист: {sheets_manager.worksheet.title}")
            logger.info(f"📝 Заголовков: {len(sheets_manager.HEADERS)}")
        else:
            logger.warning("⚠️ Google Sheets отключен или не настроен")
            logger.info("Проверьте настройки в файле .env")

    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации: {e}")
        logger.info("\nПроверьте:")
        logger.info("1. Файл credentials/google_service_account.json существует")
        logger.info("2. GOOGLE_SPREADSHEET_ID правильно указан в .env")
        logger.info("3. Сервисному аккаунту предоставлен доступ к таблице")
        return 1

    return 0

if __name__ == '__main__':
    exit(main())

"""
Скрипт для ручной синхронизации принятых объявлений с Google Sheets
Используется для восстановления синхронизации после сбоев сети
"""
import sys
import os
# Добавить корень проекта в sys.path для импортов
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from database.models import get_session, Announcement
from utils.google_sheets import GoogleSheetsManager
from utils.logger import logger


def sync_accepted_announcements():
    """
    Синхронизировать все принятые объявления с актуальным дедлайном
    """
    logger.info("🔄 Запуск ручной синхронизации с Google Sheets...")

    # Инициализация Google Sheets с retry
    sheets_manager = GoogleSheetsManager()

    if not sheets_manager.enabled:
        logger.error("❌ Google Sheets недоступен. Проверьте:")
        logger.error("   1. Подключение к интернету")
        logger.error("   2. Настройки в .env (GOOGLE_SHEETS_ENABLED=True)")
        logger.error("   3. Наличие файла credentials/google_service_account.json")
        logger.error("   4. ID таблицы в .env (GOOGLE_SPREADSHEET_ID)")

        # Попытка повторной инициализации
        logger.info("🔄 Попытка повторной инициализации...")
        if not sheets_manager.retry_initialization():
            logger.error("❌ Не удалось инициализировать Google Sheets")
            return

    # Получить сессию БД
    session = get_session()
    try:
        # Текущее время для фильтрации
        now = datetime.utcnow()

        # Запросить все accepted объявления с актуальным дедлайном
        announcements = session.query(Announcement).filter(
            Announcement.status == 'accepted',
            Announcement.application_deadline >= now
        ).all()

        logger.info(f"📊 Найдено принятых объявлений с актуальным дедлайном: {len(announcements)}")

        if not announcements:
            logger.info("✅ Нет объявлений для синхронизации")
            return

        # Синхронизация каждого объявления
        success_count = 0
        error_count = 0

        for announcement in announcements:
            try:
                # Попытка синхронизации
                result = sheets_manager.add_announcement(announcement)

                if result:
                    success_count += 1
                    logger.info(f"✓ {announcement.announcement_number}")
                else:
                    error_count += 1
                    logger.warning(f"✗ {announcement.announcement_number}")

            except Exception as e:
                error_count += 1
                logger.error(f"✗ {announcement.announcement_number}: {e}")

        # Вывод итоговой статистики
        logger.info("")
        logger.info("=" * 60)
        logger.success(f"✅ Синхронизация завершена!")
        logger.info(f"   Успешно: {success_count}")
        logger.info(f"   Ошибок:  {error_count}")
        logger.info(f"   Всего:   {len(announcements)}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Ошибка при синхронизации: {e}", exc_info=True)
    finally:
        session.close()


if __name__ == '__main__':
    sync_accepted_announcements()

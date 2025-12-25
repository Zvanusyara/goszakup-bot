"""
Главный файл запуска системы мониторинга госзакупок
"""
import asyncio
import sys
from datetime import datetime

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import TELEGRAM_BOT_TOKEN, PARSE_INTERVAL_HOURS, ALL_KEYWORDS
from database.models import init_database
from database.crud import AnnouncementCRUD, ParsingLogCRUD
from parsers.goszakup import GoszakupParser
from parsers.matcher import ManagerMatcher
from bot.handlers import get_dispatcher
from bot.notifier import TelegramNotifier
from utils.logger import logger


class GoszakupMonitoringSystem:
    """Главный класс системы мониторинга"""

    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.dp = get_dispatcher()
        self.parser = GoszakupParser()
        self.matcher = ManagerMatcher()
        self.notifier = TelegramNotifier()
        self.scheduler = AsyncIOScheduler()

    async def parse_and_notify(self):
        """Парсинг лотов и отправка уведомлений"""
        logger.info("🚀 Запуск парсинга...")

        # Создать лог парсинга
        log = ParsingLogCRUD.create()

        try:
            # Парсинг лотов
            found_lots = self.parser.search_lots(ALL_KEYWORDS, days_back=7)

            total_found = len(found_lots)
            new_added = 0
            duplicates = 0

            logger.info(f"📊 Найдено лотов: {total_found}")

            for lot_data in found_lots:
                # Проверить на дубликат
                if AnnouncementCRUD.exists(lot_data['announcement_number']):
                    duplicates += 1
                    logger.debug(f"⏭️ Пропуск дубликата: {lot_data['announcement_number']}")
                    continue

                # Найти менеджера
                manager_info = self.matcher.find_manager(lot_data)

                if not manager_info:
                    logger.warning(f"⚠️ Менеджер не найден для региона: {lot_data['region']}")
                    continue

                # Добавить информацию о менеджере к данным
                lot_data['manager_id'] = manager_info['manager_id']
                lot_data['manager_name'] = manager_info['manager_name']

                # Сохранить в БД
                announcement = AnnouncementCRUD.create(lot_data)
                new_added += 1

                logger.info(f"✅ Новое объявление добавлено: {announcement.announcement_number}")

                # Отправить уведомление менеджеру
                await self.notifier.send_to_manager(
                    telegram_id=manager_info['telegram_id'],
                    announcement=lot_data,
                    announcement_db_id=announcement.id
                )

                # Отправить уведомление админу
                await self.notifier.send_to_admin(lot_data)

                # Небольшая задержка между уведомлениями
                await asyncio.sleep(1)

            # Обновить лог парсинга
            ParsingLogCRUD.update(
                log.id,
                finished_at=datetime.utcnow(),
                total_found=total_found,
                new_added=new_added,
                duplicates=duplicates,
                status='completed'
            )

            logger.info(f"✅ Парсинг завершен. Новых: {new_added}, Дубликатов: {duplicates}")

        except Exception as e:
            logger.error(f"❌ Ошибка при парсинге: {e}")

            # Обновить лог с ошибкой
            ParsingLogCRUD.update(
                log.id,
                finished_at=datetime.utcnow(),
                status='failed',
                error_message=str(e)
            )

    async def start_parsing_schedule(self):
        """Запустить планировщик парсинга"""
        # Добавить задачу в планировщик
        self.scheduler.add_job(
            self.parse_and_notify,
            'interval',
            minutes=1,  # Для тестирования - каждую минуту
            id='parse_goszakup',
            replace_existing=True
        )

        # Запустить парсинг сразу при старте
        await self.parse_and_notify()

        # Запустить планировщик
        self.scheduler.start()

        logger.info(f"⏰ Планировщик запущен. Интервал: 1 минута (тестовый режим)")

    async def start(self):
        """Запуск системы"""
        logger.info("=" * 60)
        logger.info("🚀 Запуск системы мониторинга госзакупок Казахстана")
        logger.info("=" * 60)

        # Инициализация БД
        logger.info("📊 Инициализация базы данных...")
        init_database()

        # Запуск планировщика парсинга
        logger.info("⏰ Запуск планировщика парсинга...")
        await self.start_parsing_schedule()

        # Запуск Telegram бота
        logger.info("🤖 Запуск Telegram бота...")
        try:
            await self.dp.start_polling(self.bot, skip_updates=True)
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске бота: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Очистка ресурсов при завершении"""
        logger.info("🧹 Очистка ресурсов...")
        self.scheduler.shutdown()
        await self.notifier.close()
        await self.bot.session.close()


def main():
    """Точка входа"""
    try:
        system = GoszakupMonitoringSystem()
        asyncio.run(system.start())
    except KeyboardInterrupt:
        logger.info("\n⚠️ Остановка системы пользователем...")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

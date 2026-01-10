"""
Главный файл запуска системы мониторинга госзакупок
"""
import asyncio
import sys
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import TELEGRAM_BOT_TOKEN, PARSE_INTERVAL_HOURS, ALL_KEYWORDS, MANAGERS
from database.models import init_database, get_session, Announcement
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
            # Парсинг объявлений (проверяем только за последние сутки)
            found_announcements = self.parser.search_lots(ALL_KEYWORDS, days_back=1)

            total_found = len(found_announcements)
            new_added = 0
            duplicates = 0

            logger.info(f"📊 Найдено объявлений: {total_found}")

            for announcement_data in found_announcements:
                # Логируем количество лотов
                lots = announcement_data.get('lots', [])
                lot_count = len(lots) if lots else 1
                logger.info(f"📦 Объявление {announcement_data['announcement_number']}: {lot_count} лот(ов)")

                # Проверить на дубликат (не выводим в лог каждый дубликат)
                if AnnouncementCRUD.exists(announcement_data['announcement_number']):
                    duplicates += 1
                    continue

                # Найти всех подходящих менеджеров
                managers_info = self.matcher.find_managers(announcement_data)

                if not managers_info:
                    logger.warning(f"⚠️ Менеджеры не найдены для региона: {announcement_data['region']}")
                    continue

                # Проверяем, сколько менеджеров найдено
                is_shared = len(managers_info) > 1

                if is_shared:
                    # Объявление для нескольких менеджеров (Алматы) - не устанавливаем manager_id
                    logger.info(f"📋 Общее объявление для {len(managers_info)} менеджеров (Алматы)")
                    announcement_data['manager_id'] = None
                    announcement_data['manager_name'] = None
                else:
                    # Объявление для одного менеджера
                    manager_info = managers_info[0]
                    announcement_data['manager_id'] = manager_info['manager_id']
                    announcement_data['manager_name'] = manager_info['manager_name']

                # Сохранить в БД
                announcement = AnnouncementCRUD.create(announcement_data)
                new_added += 1

                logger.info(f"✅ Новое объявление добавлено: {announcement.announcement_number}")

                # Отправить уведомления всем подходящим менеджерам
                for manager_info in managers_info:
                    await self.notifier.send_to_manager(
                        telegram_id=manager_info['telegram_id'],
                        announcement=announcement_data,
                        announcement_db_id=announcement.id,
                        is_shared=is_shared
                    )
                    # Небольшая задержка между уведомлениями
                    await asyncio.sleep(1)

            # Обновить лог парсинга
            ParsingLogCRUD.update(
                log.id,
                finished_at=datetime.now(timezone.utc),
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
                finished_at=datetime.now(timezone.utc),
                status='failed',
                error_message=str(e)
            )

    async def check_deadlines(self):
        """Проверка дедлайнов и отправка напоминаний"""
        logger.info("⏰ Проверка дедлайнов...")

        # Текущее время (UTC)
        now = datetime.now(timezone.utc)

        # Время Астаны (UTC+5)
        kazakhstan_time = now + timedelta(hours=5)
        current_hour = kazakhstan_time.hour

        # Не отправлять уведомления ночью (с 23:00 до 8:00)
        if current_hour >= 23 or current_hour < 8:
            logger.info(f"⏸️ Ночное время ({current_hour:02d}:00 по Астане), напоминания не отправляются")
            return

        session = get_session()
        try:
            # Получить все принятые объявления с дедлайном
            announcements = session.query(Announcement).filter(
                Announcement.status == 'accepted',
                Announcement.application_deadline.isnot(None),
                Announcement.manager_id.isnot(None)
            ).all()

            reminders_sent = 0

            for announcement in announcements:
                # Вычислить время до дедлайна
                time_left = announcement.application_deadline - now
                hours_left = time_left.total_seconds() / 3600

                # Пропустить уже прошедшие дедлайны
                if hours_left < 0:
                    continue

                # Получить telegram_id менеджера
                manager_id = announcement.manager_id
                if manager_id not in MANAGERS:
                    continue

                telegram_id = MANAGERS[manager_id]['telegram_id']
                if not telegram_id:
                    continue

                # Определить, какое напоминание отправить
                reminder_sent = False

                # Напоминание за 48 часов
                if 47 <= hours_left <= 49 and not announcement.reminder_48h_sent:
                    await self.notifier.send_deadline_reminder(telegram_id, announcement, 48)
                    announcement.reminder_48h_sent = True
                    reminder_sent = True
                    reminders_sent += 1

                # Напоминание за 24 часа
                elif 23 <= hours_left <= 25 and not announcement.reminder_24h_sent:
                    await self.notifier.send_deadline_reminder(telegram_id, announcement, 24)
                    announcement.reminder_24h_sent = True
                    reminder_sent = True
                    reminders_sent += 1

                # Напоминание за 2 часа
                elif 1.5 <= hours_left <= 2.5 and not announcement.reminder_2h_sent:
                    await self.notifier.send_deadline_reminder(telegram_id, announcement, 2)
                    announcement.reminder_2h_sent = True
                    reminder_sent = True
                    reminders_sent += 1

                if reminder_sent:
                    session.commit()
                    await asyncio.sleep(1)  # Задержка между уведомлениями

            logger.info(f"✅ Проверка дедлайнов завершена. Отправлено напоминаний: {reminders_sent}")

        except Exception as e:
            logger.error(f"❌ Ошибка при проверке дедлайнов: {e}")
            session.rollback()
        finally:
            session.close()

    async def start_parsing_schedule(self):
        """Запустить планировщик парсинга и проверки дедлайнов"""
        # Добавить задачу парсинга в планировщик
        self.scheduler.add_job(
            self.parse_and_notify,
            'interval',
            minutes=1,  # Для тестирования - каждую минуту
            id='parse_goszakup',
            replace_existing=True
        )

        # Добавить задачу проверки дедлайнов (каждый час)
        self.scheduler.add_job(
            self.check_deadlines,
            'interval',
            hours=1,
            id='check_deadlines',
            replace_existing=True
        )

        # Запустить парсинг сразу при старте
        await self.parse_and_notify()

        # Запустить проверку дедлайнов сразу при старте
        await self.check_deadlines()

        # Запустить планировщик
        self.scheduler.start()

        logger.info(f"⏰ Планировщик запущен. Парсинг: каждую 1 мин, проверка дедлайнов: каждый час")

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

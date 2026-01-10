"""
Модуль для отправки уведомлений через Telegram
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from bot.messages import format_announcement_message, format_coordinator_notification, format_deadline_reminder
from bot.keyboards import get_announcement_keyboard, get_almaty_claim_keyboard
from config import TELEGRAM_BOT_TOKEN, ADMIN_TELEGRAM_ID, COORDINATOR_TELEGRAM_ID


class TelegramNotifier:
    """Класс для отправки уведомлений в Telegram"""

    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)

    async def send_to_manager(self, telegram_id: int, announcement: dict, announcement_db_id: int, is_shared: bool = False):
        """
        Отправить уведомление менеджеру

        Args:
            telegram_id: Telegram ID менеджера
            announcement: Данные объявления
            announcement_db_id: ID объявления в базе данных
            is_shared: Если True, объявление общее (Алматы) - показать кнопку "Мой район"
        """
        print(f"📤 Попытка отправки уведомления менеджеру {announcement.get('manager_name', 'N/A')} (ID: {telegram_id})")

        message_text = format_announcement_message(announcement, for_manager=True)

        # Выбор клавиатуры в зависимости от типа объявления
        if is_shared:
            keyboard = get_almaty_claim_keyboard(announcement_db_id)
            print(f"   📍 Общее объявление (Алматы) - кнопка 'Мой район'")
        else:
            keyboard = get_announcement_keyboard(announcement_db_id)

        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message_text,
                reply_markup=keyboard,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            print(f"✅ Уведомление успешно отправлено менеджеру (ID: {telegram_id})")
            return True

        except Exception as e:
            print(f"❌ ОШИБКА отправки менеджеру (ID: {telegram_id}): {e}")
            print(f"   ⚠️ Возможно, менеджер не запустил бота (/start)")
            return False

    async def send_to_admin(self, announcement: dict):
        """
        Отправить уведомление администратору

        Args:
            announcement: Данные объявления с информацией о менеджере
        """
        if not ADMIN_TELEGRAM_ID or ADMIN_TELEGRAM_ID == 'YOUR_ADMIN_ID':
            print("⚠️ ADMIN_TELEGRAM_ID не настроен, уведомление не отправлено")
            return False

        message_text = format_announcement_message(announcement, for_manager=False)

        try:
            await self.bot.send_message(
                chat_id=int(ADMIN_TELEGRAM_ID),
                text=message_text,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            print(f"✅ Уведомление отправлено админу (ID: {ADMIN_TELEGRAM_ID})")
            return True

        except Exception as e:
            print(f"❌ Ошибка отправки админу: {e}")
            return False

    async def send_to_coordinator(self, announcement_number: str, announcement_url: str,
                                  manager_name: str, application_deadline):
        """
        Отправить уведомление координатору о принятом объявлении

        Args:
            announcement_number: Номер объявления
            announcement_url: Ссылка на объявление
            manager_name: Имя менеджера
            application_deadline: Срок окончания приема заявок
        """
        if not COORDINATOR_TELEGRAM_ID:
            print("⚠️ COORDINATOR_TELEGRAM_ID не настроен, уведомление не отправлено")
            return False

        message_text = format_coordinator_notification(
            announcement_number,
            announcement_url,
            manager_name,
            application_deadline
        )

        try:
            await self.bot.send_message(
                chat_id=int(COORDINATOR_TELEGRAM_ID),
                text=message_text,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            print(f"✅ Уведомление отправлено координатору (ID: {COORDINATOR_TELEGRAM_ID})")
            return True

        except Exception as e:
            print(f"❌ Ошибка отправки координатору: {e}")
            return False

    async def send_deadline_reminder(self, telegram_id: int, announcement, hours_left: int):
        """
        Отправить напоминание о приближающемся дедлайне

        Args:
            telegram_id: Telegram ID менеджера
            announcement: Объект объявления из БД
            hours_left: Часов до окончания срока (48, 24, 2)
        """
        print(f"⏰ Отправка напоминания о дедлайне менеджеру (ID: {telegram_id}), осталось {hours_left}ч")

        message_text = format_deadline_reminder(announcement, hours_left)

        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message_text,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            print(f"✅ Напоминание отправлено менеджеру (ID: {telegram_id})")
            return True

        except Exception as e:
            print(f"❌ Ошибка отправки напоминания менеджеру (ID: {telegram_id}): {e}")
            return False

    async def close(self):
        """Закрыть сессию бота"""
        await self.bot.session.close()

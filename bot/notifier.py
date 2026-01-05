"""
Модуль для отправки уведомлений через Telegram
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from bot.messages import format_announcement_message
from bot.keyboards import get_announcement_keyboard
from config import TELEGRAM_BOT_TOKEN, ADMIN_TELEGRAM_ID


class TelegramNotifier:
    """Класс для отправки уведомлений в Telegram"""

    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)

    async def send_to_manager(self, telegram_id: int, announcement: dict, announcement_db_id: int):
        """
        Отправить уведомление менеджеру

        Args:
            telegram_id: Telegram ID менеджера
            announcement: Данные объявления
            announcement_db_id: ID объявления в базе данных
        """
        print(f"📤 Попытка отправки уведомления менеджеру {announcement.get('manager_name', 'N/A')} (ID: {telegram_id})")

        message_text = format_announcement_message(announcement, for_manager=True)
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

    async def close(self):
        """Закрыть сессию бота"""
        await self.bot.session.close()

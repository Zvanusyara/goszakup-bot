"""
Клавиатуры для Telegram бота
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_announcement_keyboard(announcement_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопками для объявления

    Args:
        announcement_id: ID объявления в базе данных

    Returns:
        InlineKeyboardMarkup с кнопками
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Принять",
                callback_data=f"accept_{announcement_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"reject_{announcement_id}"
            )
        ]
    ])

    return keyboard

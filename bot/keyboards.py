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


def get_admin_dashboard_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для главного дашборда администратора

    Returns:
        InlineKeyboardMarkup с кнопками управления
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔍 Подробная статистика",
                callback_data="admin_detailed_stats"
            )
        ],
        [
            InlineKeyboardButton(
                text="⚠️ Проблемные",
                callback_data="admin_problem_announcements"
            ),
            InlineKeyboardButton(
                text="📋 Все объявления",
                callback_data="admin_all_announcements"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data="admin_refresh_dashboard"
            )
        ]
    ])

    return keyboard

"""
Клавиатуры для Telegram бота
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


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
                text="✅ Беру в работу",
                callback_data=f"accept_{announcement_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"reject_{announcement_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="⏸️ Отложить",
                callback_data=f"postpone_{announcement_id}"
            )
        ]
    ])

    return keyboard


def get_almaty_claim_keyboard(announcement_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой "Мой район" для объявлений из Алматы

    Args:
        announcement_id: ID объявления в базе данных

    Returns:
        InlineKeyboardMarkup с кнопкой
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📍 Мой район",
                callback_data=f"claim_almaty_{announcement_id}"
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


def get_work_announcements_keyboard(announcements: list) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком объявлений в работе

    Args:
        announcements: Список объявлений

    Returns:
        InlineKeyboardMarkup с кнопками объявлений
    """
    buttons = []

    for announcement in announcements:
        # Эмодзи в зависимости от статуса обработки
        emoji = "✅" if announcement.is_processed else "📄"
        # Короткий номер объявления для отображения
        short_number = announcement.announcement_number[:20] + "..." if len(
            announcement.announcement_number) > 20 else announcement.announcement_number

        buttons.append([
            InlineKeyboardButton(
                text=f"{emoji} {short_number}",
                callback_data=f"work_view_{announcement.id}"
            )
        ])

    # Добавить кнопку "Назад"
    buttons.append([
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="close_message"
        )
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_announcement_actions_keyboard(announcement_id: int, is_processed: bool) -> InlineKeyboardMarkup:
    """
    Клавиатура с действиями для объявления в работе

    Args:
        announcement_id: ID объявления
        is_processed: Обработано ли объявление

    Returns:
        InlineKeyboardMarkup с кнопками действий
    """
    buttons = []

    if not is_processed:
        # Если не обработано - показываем кнопку "Обработал"
        buttons.append([
            InlineKeyboardButton(
                text="✅ Обработал",
                callback_data=f"work_processed_{announcement_id}"
            )
        ])

    # Кнопка "Подробности" всегда доступна
    buttons.append([
        InlineKeyboardButton(
            text="📋 Подробности",
            callback_data=f"work_details_{announcement_id}"
        )
    ])

    # Кнопка "Назад к списку"
    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад к списку",
            callback_data="work_back_to_list"
        )
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_manager_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Главная клавиатура для менеджера

    Returns:
        ReplyKeyboardMarkup с основными кнопками менеджера
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Объявления в работе"),
                KeyboardButton(text="📊 Статистика")
            ],
            [
                KeyboardButton(text="🔔 Не принятые")
            ],
            [
                KeyboardButton(text="ℹ️ Справка")
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )
    return keyboard


def get_pending_announcements_keyboard(announcements: list) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком не принятых объявлений

    Args:
        announcements: Список объявлений

    Returns:
        InlineKeyboardMarkup с кнопками объявлений
    """
    buttons = []

    for announcement in announcements:
        # Короткий номер объявления для отображения
        short_number = announcement.announcement_number[:20] + "..." if len(
            announcement.announcement_number) > 20 else announcement.announcement_number

        buttons.append([
            InlineKeyboardButton(
                text=f"🔔 {short_number}",
                callback_data=f"pending_view_{announcement.id}"
            )
        ])

    # Добавить кнопку "Назад"
    buttons.append([
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="close_message"
        )
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_stats_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для статистики менеджера

    Returns:
        InlineKeyboardMarkup с кнопкой "Назад"
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="close_message"
            )
        ]
    ])
    return keyboard


def get_admin_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Главная клавиатура для администратора

    Returns:
        ReplyKeyboardMarkup с основными кнопками админа
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👔 Админ-панель")
            ],
            [
                KeyboardButton(text="👤 Олеся"),
                KeyboardButton(text="👤 Анастасия")
            ],
            [
                KeyboardButton(text="👤 Жасулан"),
                KeyboardButton(text="👤 Алибек")
            ],
            [
                KeyboardButton(text="ℹ️ Справка")
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )
    return keyboard


def get_manager_menu_keyboard(manager_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура главного меню менеджера для админа

    Args:
        manager_id: ID менеджера

    Returns:
        InlineKeyboardMarkup с 4 кнопками разделов
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📊 Статистика",
                callback_data=f"manager_{manager_id}_stats"
            )
        ],
        [
            InlineKeyboardButton(
                text="⚠️ Проблемные",
                callback_data=f"manager_{manager_id}_problems"
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 Активные",
                callback_data=f"manager_{manager_id}_active"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Действия",
                callback_data=f"manager_{manager_id}_actions"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Закрыть",
                callback_data="close_message"
            )
        ]
    ])

    return keyboard


def get_manager_back_keyboard(manager_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой 'Назад' к меню менеджера

    Args:
        manager_id: ID менеджера

    Returns:
        InlineKeyboardMarkup с кнопкой "Назад"
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=f"manager_{manager_id}_back"
            )
        ]
    ])

    return keyboard


def get_problem_announcements_keyboard(manager_id: int, problems: dict) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком проблемных объявлений

    Args:
        manager_id: ID менеджера
        problems: Словарь с проблемными объявлениями

    Returns:
        InlineKeyboardMarkup с кнопками объявлений
    """
    buttons = []

    # Pending >24ч
    pending_24h = problems['pending_24h']
    if pending_24h:
        for ann in pending_24h[:5]:  # Первые 5
            short_number = ann.announcement_number[:20] + "..." if len(
                ann.announcement_number) > 20 else ann.announcement_number

            buttons.append([
                InlineKeyboardButton(
                    text=f"🔴 {short_number}",
                    callback_data=f"manager_{manager_id}_view_{ann.id}"
                )
            ])

    # Accepted >48ч
    accepted_48h = problems['accepted_48h']
    if accepted_48h:
        for ann in accepted_48h[:5]:  # Первые 5
            short_number = ann.announcement_number[:20] + "..." if len(
                ann.announcement_number) > 20 else ann.announcement_number

            buttons.append([
                InlineKeyboardButton(
                    text=f"🟡 {short_number}",
                    callback_data=f"manager_{manager_id}_view_{ann.id}"
                )
            ])

    # Кнопка "Назад"
    buttons.append([
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=f"manager_{manager_id}_back"
        )
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_active_announcements_keyboard(manager_id: int, active: list) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком активных объявлений

    Args:
        manager_id: ID менеджера
        active: Список активных объявлений

    Returns:
        InlineKeyboardMarkup с кнопками объявлений
    """
    buttons = []

    # Первые 10 объявлений
    for ann in active[:10]:
        short_number = ann.announcement_number[:20] + "..." if len(
            ann.announcement_number) > 20 else ann.announcement_number

        buttons.append([
            InlineKeyboardButton(
                text=f"📋 {short_number}",
                callback_data=f"manager_{manager_id}_view_{ann.id}"
            )
        ])

    # Кнопка "Назад"
    buttons.append([
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=f"manager_{manager_id}_back"
        )
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_announcement_detail_keyboard(manager_id: int, announcement_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для просмотра деталей объявления из списка менеджера

    Args:
        manager_id: ID менеджера
        announcement_id: ID объявления

    Returns:
        InlineKeyboardMarkup с кнопкой "Назад"
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔙 Назад к списку",
                callback_data=f"manager_{manager_id}_back"
            )
        ]
    ])

    return keyboard


def get_coordinator_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Главная клавиатура для координатора

    Returns:
        ReplyKeyboardMarkup с кнопкой "Объявления в работе"
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Объявления в работе")
            ],
            [
                KeyboardButton(text="ℹ️ Справка")
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )
    return keyboard


def get_coordinator_announcements_keyboard(announcements: list) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком объявлений в работе для координатора

    Args:
        announcements: Список объявлений

    Returns:
        InlineKeyboardMarkup с кнопками объявлений
    """
    buttons = []

    for announcement in announcements:
        # Короткий номер объявления для отображения
        short_number = announcement.announcement_number[:20] + "..." if len(
            announcement.announcement_number) > 20 else announcement.announcement_number

        buttons.append([
            InlineKeyboardButton(
                text=f"📋 {short_number}",
                callback_data=f"coord_view_{announcement.id}"
            )
        ])

    # Добавить кнопку "Закрыть"
    buttons.append([
        InlineKeyboardButton(
            text="🔙 Закрыть",
            callback_data="close_message"
        )
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_coordinator_announcement_detail_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для просмотра деталей объявления координатором

    Returns:
        InlineKeyboardMarkup с кнопкой "Назад"
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔙 Назад к списку",
                callback_data="coord_back_to_list"
            )
        ]
    ])

    return keyboard

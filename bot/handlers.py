"""
Обработчики команд и callback-кнопок Telegram бота
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

from database.crud import AnnouncementCRUD, ManagerActionCRUD
from database.models import get_session, Announcement
from bot.messages import (
    START_MESSAGE,
    HELP_MESSAGE,
    COORDINATOR_START_MESSAGE,
    format_accepted_notification,
    format_rejected_notification,
    format_stats_message,
    format_admin_dashboard,
    format_work_announcements_list,
    format_announcement_details,
    format_manager_menu,
    format_manager_statistics,
    format_problem_announcements,
    format_active_announcements,
    format_manager_actions,
    format_coordinator_announcements_list,
    format_coordinator_announcement_details
)
from bot.keyboards import (
    get_admin_dashboard_keyboard,
    get_work_announcements_keyboard,
    get_announcement_actions_keyboard,
    get_manager_main_keyboard,
    get_admin_main_keyboard,
    get_announcement_keyboard,
    get_manager_menu_keyboard,
    get_manager_back_keyboard,
    get_problem_announcements_keyboard,
    get_active_announcements_keyboard,
    get_announcement_detail_keyboard,
    get_coordinator_main_keyboard,
    get_coordinator_announcements_keyboard,
    get_coordinator_announcement_detail_keyboard
)
from config import TELEGRAM_BOT_TOKEN, ADMIN_TELEGRAM_ID, COORDINATOR_TELEGRAM_ID, MANAGERS
from sqlalchemy import func
from datetime import datetime, timedelta


async def safe_callback_answer(callback: CallbackQuery, text: str = None, show_alert: bool = False):
    """
    Безопасный ответ на callback query с обработкой timeout ошибок
    """
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except TelegramBadRequest as e:
        if "query is too old" in str(e) or "query ID is invalid" in str(e):
            # Игнорируем ошибки устаревших callback'ов
            pass
        else:
            # Другие ошибки пробрасываем дальше
            raise


router = Router()


def get_user_keyboard(user_id: int):
    """Получить клавиатуру для пользователя в зависимости от его роли"""
    # Проверяем, является ли пользователь админом
    is_admin = ADMIN_TELEGRAM_ID and str(user_id) == str(ADMIN_TELEGRAM_ID)

    # Проверяем, является ли пользователь координатором
    is_coordinator = COORDINATOR_TELEGRAM_ID and str(user_id) == str(COORDINATOR_TELEGRAM_ID)

    # Проверяем, является ли пользователь менеджером
    is_manager = False
    for mid, mdata in MANAGERS.items():
        if mdata['telegram_id'] == user_id:
            is_manager = True
            break

    # Возвращаем клавиатуру в зависимости от роли
    if is_admin:
        return get_admin_main_keyboard()
    elif is_coordinator:
        return get_coordinator_main_keyboard()
    elif is_manager:
        return get_manager_main_keyboard()
    else:
        return None



# FSM для получения причины отказа
class RejectionState(StatesGroup):
    waiting_for_reason = State()


# FSM для получения деталей участия
class ParticipationState(StatesGroup):
    waiting_for_details = State()


@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    keyboard = get_user_keyboard(user_id)

    # Проверяем, является ли пользователь координатором
    is_coordinator = COORDINATOR_TELEGRAM_ID and str(user_id) == str(COORDINATOR_TELEGRAM_ID)

    # Отправляем соответствующее сообщение
    if is_coordinator:
        await message.answer(COORDINATOR_START_MESSAGE, parse_mode='HTML', reply_markup=keyboard)
    else:
        await message.answer(START_MESSAGE, parse_mode='HTML', reply_markup=keyboard)


@router.message(Command("help"))
async def cmd_help(message: Message):
    keyboard = get_user_keyboard(message.from_user.id)
    await message.answer(HELP_MESSAGE, parse_mode='HTML', reply_markup=keyboard)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Обработчик команды /stats - статистика менеджера"""
    user_id = message.from_user.id

    # Найти ID менеджера по Telegram ID
    manager_id = None
    for mid, mdata in MANAGERS.items():
        if mdata['telegram_id'] == user_id:
            manager_id = mid
            break

    if not manager_id:
        await message.answer("❌ Вы не зарегистрированы как менеджер в системе.")
        return

    # Получить статистику из БД
    session = get_session()
    try:
        total = session.query(Announcement).filter(
            Announcement.manager_id == manager_id
        ).count()

        pending = session.query(Announcement).filter(
            Announcement.manager_id == manager_id,
            Announcement.status == 'pending'
        ).count()

        accepted = session.query(Announcement).filter(
            Announcement.manager_id == manager_id,
            Announcement.status == 'accepted'
        ).count()

        rejected = session.query(Announcement).filter(
            Announcement.manager_id == manager_id,
            Announcement.status == 'rejected'
        ).count()

        stats = {
            'total': total,
            'pending': pending,
            'accepted': accepted,
            'rejected': rejected
        }

        # Используем inline клавиатуру с кнопкой "Назад"
        from bot.keyboards import get_stats_keyboard
        keyboard = get_stats_keyboard()
        await message.answer(format_stats_message(stats), parse_mode='HTML', reply_markup=keyboard)

    finally:
        session.close()


@router.message(Command("my_work"))
async def cmd_my_work(message: Message):
    """Обработчик команды /my_work - объявления в работе"""
    user_id = message.from_user.id

    # Найти ID менеджера по Telegram ID
    manager_id = None
    for mid, mdata in MANAGERS.items():
        if mdata['telegram_id'] == user_id:
            manager_id = mid
            break

    if not manager_id:
        await message.answer("❌ Вы не зарегистрированы как менеджер в системе.")
        return

    # Получить принятые объявления из БД
    announcements = AnnouncementCRUD.get_accepted_for_manager(manager_id)

    # Отправить список объявлений
    # Инлайн-клавиатура для объявлений (всегда есть кнопка "Назад")
    from bot.keyboards import get_work_announcements_keyboard, get_stats_keyboard
    if announcements:
        inline_keyboard = get_work_announcements_keyboard(announcements)
    else:
        # Если нет объявлений, все равно показываем кнопку "Назад"
        inline_keyboard = get_stats_keyboard()

    await message.answer(
        format_work_announcements_list(announcements),
        parse_mode='HTML',
        reply_markup=inline_keyboard
    )


@router.message(Command("pending"))
async def cmd_pending(message: Message):
    """Обработчик команды /pending - не принятые объявления"""
    user_id = message.from_user.id

    # Найти ID менеджера по Telegram ID
    manager_id = None
    for mid, mdata in MANAGERS.items():
        if mdata['telegram_id'] == user_id:
            manager_id = mid
            break

    if not manager_id:
        await message.answer("❌ Вы не зарегистрированы как менеджер в системе.")
        return

    # Получить не принятые объявления из БД
    session = get_session()
    try:
        announcements = session.query(Announcement).filter(
            Announcement.manager_id == manager_id,
            Announcement.status == 'pending'
        ).order_by(Announcement.created_at.desc()).all()

        # Отправить список объявлений
        from bot.keyboards import get_pending_announcements_keyboard, get_stats_keyboard
        from bot.messages import format_pending_announcements_list

        if announcements:
            inline_keyboard = get_pending_announcements_keyboard(announcements)
        else:
            # Если нет объявлений, все равно показываем кнопку "Назад"
            inline_keyboard = get_stats_keyboard()

        await message.answer(
            format_pending_announcements_list(announcements),
            parse_mode='HTML',
            reply_markup=inline_keyboard
        )
    finally:
        session.close()


def get_admin_dashboard_data() -> dict:
    """
    Получить данные для дашборда администратора из БД

    Returns:
        dict с данными для дашборда
    """
    session = get_session()
    try:
        # Начало сегодняшнего дня
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Статистика объявлений
        new = session.query(Announcement).filter(
            Announcement.status == 'pending'
        ).count()

        in_progress = session.query(Announcement).filter(
            Announcement.status == 'accepted',
            Announcement.is_processed == False
        ).count()

        processed = session.query(Announcement).filter(
            Announcement.status == 'accepted',
            Announcement.is_processed == True
        ).count()

        rejected = session.query(Announcement).filter(
            Announcement.status == 'rejected'
        ).count()

        total_today = session.query(Announcement).filter(
            Announcement.created_at >= today_start
        ).count()

        # Критические зоны
        # Зависли >24ч (pending более 24 часов)
        stuck_24h_threshold = datetime.now() - timedelta(hours=24)
        stuck_24h = session.query(Announcement).filter(
            Announcement.status == 'pending',
            Announcement.created_at < stuck_24h_threshold
        ).count()

        # Без ответа >2ч (pending более 2 часов)
        no_response_2h_threshold = datetime.now() - timedelta(hours=2)
        no_response_2h = session.query(Announcement).filter(
            Announcement.status == 'pending',
            Announcement.created_at < no_response_2h_threshold
        ).count()

        # Нужно внимание = зависшие + без ответа (уникальные)
        needs_attention = stuck_24h + no_response_2h

        return {
            'new': new,
            'in_progress': in_progress,
            'processed': processed,
            'rejected': rejected,
            'total_today': total_today,
            'stuck_24h': stuck_24h,
            'no_response_2h': no_response_2h,
            'needs_attention': needs_attention
        }

    finally:
        session.close()


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Обработчик команды /admin - дашборд администратора"""
    user_id = message.from_user.id

    # Проверка прав администратора
    if ADMIN_TELEGRAM_ID and str(user_id) != str(ADMIN_TELEGRAM_ID):
        await message.answer("❌ У вас нет прав администратора.")
        return

    # Получить данные для дашборда
    dashboard_data = get_admin_dashboard_data()

    # Отправить дашборд с клавиатурой
    await message.answer(
        format_admin_dashboard(dashboard_data),
        parse_mode='HTML',
        reply_markup=get_admin_dashboard_keyboard()
    )


@router.callback_query(F.data.startswith("accept_"))
async def callback_accept(callback: CallbackQuery, bot: Bot):
    """Обработчик нажатия кнопки 'Беру в работу'"""
    announcement_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    # Найти менеджера
    manager_id = None
    manager_name = None
    for mid, mdata in MANAGERS.items():
        if mdata['telegram_id'] == user_id:
            manager_id = mid
            manager_name = mdata['name']
            break

    if not manager_id:
        await callback.answer("❌ Вы не авторизованы", show_alert=True)
        return

    # Обновить статус в БД
    AnnouncementCRUD.update_status(announcement_id, 'accepted')

    # Записать действие
    ManagerActionCRUD.create({
        'announcement_id': announcement_id,
        'manager_id': manager_id,
        'manager_name': manager_name,
        'telegram_id': user_id,
        'action': 'accepted'
    })

    # Получить данные объявления для уведомлений
    session = get_session()
    try:
        announcement = session.query(Announcement).filter(
            Announcement.id == announcement_id
        ).first()

        if announcement:
            # Уведомить админа
            if ADMIN_TELEGRAM_ID and ADMIN_TELEGRAM_ID != 'YOUR_ADMIN_ID':
                admin_message = format_accepted_notification(
                    announcement.announcement_number,
                    manager_name
                )
                try:
                    await bot.send_message(
                        int(ADMIN_TELEGRAM_ID),
                        admin_message,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    print(f"⚠️ Не удалось отправить уведомление админу: {e}")

            # Уведомить координатора
            from bot.notifier import TelegramNotifier
            notifier = TelegramNotifier()
            try:
                await notifier.send_to_coordinator(
                    announcement_number=announcement.announcement_number,
                    announcement_url=announcement.announcement_url,
                    manager_name=manager_name,
                    application_deadline=announcement.application_deadline
                )
            except Exception as e:
                print(f"⚠️ Не удалось отправить уведомление координатору: {e}")

    finally:
        session.close()

    # Обновить сообщение
    await callback.message.edit_text(
        f"{callback.message.text}\n\n✅ <b>Статус: ПРИНЯТО</b>",
        parse_mode='HTML'
    )

    await callback.answer("✅ Объявление принято в работу!", show_alert=True)


@router.callback_query(F.data.startswith("reject_"))
async def callback_reject(callback: CallbackQuery, state: FSMContext):
    """Обработчик нажатия кнопки 'Отклонить'"""
    announcement_id = int(callback.data.split("_")[1])

    # Сохранить ID объявления в состоянии
    await state.update_data(announcement_id=announcement_id)
    await state.set_state(RejectionState.waiting_for_reason)

    await callback.message.answer(
        "📝 Пожалуйста, укажите причину отказа:",
        parse_mode='HTML'
    )

    await callback.answer()


@router.message(StateFilter(RejectionState.waiting_for_reason))
async def process_rejection_reason(message: Message, state: FSMContext, bot: Bot):
    """Обработчик причины отказа"""
    reason = message.text
    data = await state.get_data()
    announcement_id = data.get('announcement_id')

    user_id = message.from_user.id

    # Найти менеджера
    manager_id = None
    manager_name = None
    for mid, mdata in MANAGERS.items():
        if mdata['telegram_id'] == user_id:
            manager_id = mid
            manager_name = mdata['name']
            break

    if not manager_id:
        await message.answer("❌ Вы не авторизованы")
        await state.clear()
        return

    # Обновить статус в БД
    AnnouncementCRUD.update_status(announcement_id, 'rejected', reason)

    # Записать действие
    ManagerActionCRUD.create({
        'announcement_id': announcement_id,
        'manager_id': manager_id,
        'manager_name': manager_name,
        'telegram_id': user_id,
        'action': 'rejected',
        'comment': reason
    })

    # Получить данные объявления для уведомления админа
    session = get_session()
    try:
        announcement = session.query(Announcement).filter(
            Announcement.id == announcement_id
        ).first()

        if announcement:
            # Уведомить админа
            if ADMIN_TELEGRAM_ID and ADMIN_TELEGRAM_ID != 'YOUR_ADMIN_ID':
                admin_message = format_rejected_notification(
                    announcement.announcement_number,
                    manager_name,
                    reason
                )
                try:
                    await bot.send_message(
                        int(ADMIN_TELEGRAM_ID),
                        admin_message,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    print(f"⚠️ Не удалось отправить уведомление админу: {e}")

    finally:
        session.close()

    await message.answer(
        f"❌ Объявление отклонено.\n\n📝 Причина: {reason}",
        parse_mode='HTML'
    )

    # Очистить состояние
    await state.clear()


@router.message(StateFilter(ParticipationState.waiting_for_details))
async def process_participation_details(message: Message, state: FSMContext):
    """Обработчик деталей участия"""
    details = message.text
    data = await state.get_data()
    announcement_id = data.get('announcement_id')
    manager_id = data.get('manager_id')
    manager_name = data.get('manager_name')

    # Обновить детали участия и отметить как обработанное
    session = get_session()
    try:
        announcement = session.query(Announcement).filter(
            Announcement.id == announcement_id
        ).first()

        if announcement:
            announcement.participation_details = details
            announcement.is_processed = True
            session.commit()

            # Обновить в Google Sheets если включено
            from utils.google_sheets import get_sheets_manager
            sheets_manager = get_sheets_manager()
            if sheets_manager.enabled:
                sheets_manager.update_announcement(announcement)

            # Записать действие
            ManagerActionCRUD.create({
                'announcement_id': announcement_id,
                'manager_id': manager_id,
                'manager_name': manager_name,
                'telegram_id': message.from_user.id,
                'action': 'processed',
                'comment': f'Отметил как обработанное. Детали участия: {details[:100]}'
            })

            await message.answer(
                f"✅ Объявление отмечено как обработанное!\n\n"
                f"📝 Детали участия сохранены:\n{details}",
                parse_mode='HTML'
            )

    finally:
        session.close()

    # Очистить состояние
    await state.clear()


@router.callback_query(F.data == "admin_refresh_dashboard")
async def callback_refresh_dashboard(callback: CallbackQuery):
    """Обработчик кнопки 'Обновить' дашборда"""
    user_id = callback.from_user.id

    # Проверка прав администратора
    if ADMIN_TELEGRAM_ID and str(user_id) != str(ADMIN_TELEGRAM_ID):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return

    # Получить свежие данные
    dashboard_data = get_admin_dashboard_data()

    # Обновить сообщение
    try:
        await callback.message.edit_text(
            format_admin_dashboard(dashboard_data),
            parse_mode='HTML',
            reply_markup=get_admin_dashboard_keyboard()
        )
        await callback.answer("✅ Дашборд обновлен")
    except Exception as e:
        await callback.answer("⚠️ Данные не изменились", show_alert=False)


@router.callback_query(F.data.startswith("work_view_"))
async def callback_work_view(callback: CallbackQuery):
    """Обработчик просмотра объявления из списка в работе"""
    announcement_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    # Проверка авторизации менеджера
    manager_id = None
    for mid, mdata in MANAGERS.items():
        if mdata['telegram_id'] == user_id:
            manager_id = mid
            break

    if not manager_id:
        await callback.answer("❌ Вы не авторизованы", show_alert=True)
        return

    # Получить объявление из БД
    session = get_session()
    try:
        announcement = session.query(Announcement).filter(
            Announcement.id == announcement_id,
            Announcement.manager_id == manager_id
        ).first()

        if not announcement:
            await callback.answer("❌ Объявление не найдено", show_alert=True)
            return

        # Показать краткую информацию с кнопками действий
        message_text = (
            f"{'✅' if announcement.is_processed else '📄'} <b>{announcement.announcement_number}</b>\n\n"
            f"📍 {announcement.region or 'N/A'}\n"
            f"🏢 {announcement.organization_name or 'N/A'}\n\n"
            f"💼 {announcement.lot_name[:100] + '...' if announcement.lot_name and len(announcement.lot_name) > 100 else announcement.lot_name or 'N/A'}"
        )

        await callback.message.edit_text(
            message_text,
            parse_mode='HTML',
            reply_markup=get_announcement_actions_keyboard(announcement_id, announcement.is_processed)
        )
        await callback.answer()

    finally:
        session.close()


@router.callback_query(F.data.startswith("work_processed_"))
async def callback_work_processed(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Обработал'"""
    announcement_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    # Проверка авторизации менеджера
    manager_id = None
    manager_name = None
    for mid, mdata in MANAGERS.items():
        if mdata['telegram_id'] == user_id:
            manager_id = mid
            manager_name = mdata['name']
            break

    if not manager_id:
        await callback.answer("❌ Вы не авторизованы", show_alert=True)
        return

    # Сохранить ID объявления в состоянии
    await state.update_data(announcement_id=announcement_id, manager_id=manager_id, manager_name=manager_name)
    await state.set_state(ParticipationState.waiting_for_details)

    # Запросить информацию о товаре для участия
    await callback.message.answer(
        "📝 Напиши информацию о товаре для участия:",
        parse_mode='HTML'
    )

    await callback.answer()


@router.callback_query(F.data.startswith("work_details_"))
async def callback_work_details(callback: CallbackQuery):
    """Обработчик кнопки 'Подробности'"""
    announcement_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    # Проверка авторизации менеджера
    manager_id = None
    for mid, mdata in MANAGERS.items():
        if mdata['telegram_id'] == user_id:
            manager_id = mid
            break

    if not manager_id:
        await callback.answer("❌ Вы не авторизованы", show_alert=True)
        return

    # Получить объявление из БД
    session = get_session()
    try:
        announcement = session.query(Announcement).filter(
            Announcement.id == announcement_id,
            Announcement.manager_id == manager_id
        ).first()

        if not announcement:
            await callback.answer("❌ Объявление не найдено", show_alert=True)
            return

        # Показать полную информацию
        await callback.message.edit_text(
            format_announcement_details(announcement),
            parse_mode='HTML',
            reply_markup=get_announcement_actions_keyboard(announcement_id, announcement.is_processed)
        )
        await callback.answer()

    finally:
        session.close()


@router.callback_query(F.data == "work_back_to_list")
async def callback_work_back_to_list(callback: CallbackQuery):
    """Обработчик кнопки 'Назад к списку'"""
    user_id = callback.from_user.id

    # Найти ID менеджера
    manager_id = None
    for mid, mdata in MANAGERS.items():
        if mdata['telegram_id'] == user_id:
            manager_id = mid
            break

    if not manager_id:
        await callback.answer("❌ Вы не авторизованы", show_alert=True)
        return

    # Получить список объявлений
    announcements = AnnouncementCRUD.get_accepted_for_manager(manager_id)

    # Вернуться к списку
    await callback.message.edit_text(
        format_work_announcements_list(announcements),
        parse_mode='HTML',
        reply_markup=get_work_announcements_keyboard(announcements) if announcements else None
    )
    await callback.answer()

# ========================================
# Обработчики кнопок (текстовых сообщений)
# ========================================

@router.message(F.text == "📋 Объявления в работе")
async def button_my_work(message: Message):
    """Обработчик кнопки 'Объявления в работе'"""
    await cmd_my_work(message)


@router.message(F.text == "📊 Статистика")
async def button_stats(message: Message):
    """Обработчик кнопки 'Статистика'"""
    await cmd_stats(message)


@router.message(F.text == "🔔 Не принятые")
async def button_pending(message: Message):
    """Обработчик кнопки 'Не принятые'"""
    await cmd_pending(message)


@router.message(F.text == "ℹ️ Справка")
async def button_help(message: Message):
    """Обработчик кнопки 'Справка'"""
    await cmd_help(message)


@router.message(F.text == "👔 Админ-панель")
async def button_admin(message: Message):
    """Обработчик кнопки 'Админ-панель'"""
    await cmd_admin(message)


@router.callback_query(F.data == "close_message")
async def callback_close_message(callback: CallbackQuery):
    """Обработчик кнопки 'Назад' - удаляет сообщение"""
    try:
        await callback.message.delete()
        await callback.answer()
    except Exception as e:
        # Если не удалось удалить сообщение, просто отвечаем на callback
        await callback.answer("Сообщение закрыто")


@router.callback_query(F.data.startswith("pending_view_"))
async def callback_pending_view(callback: CallbackQuery, bot: Bot):
    """Обработчик просмотра не принятого объявления из списка"""
    try:
        announcement_id = int(callback.data.split("_")[2])
        user_id = callback.from_user.id

        # Найти ID менеджера по Telegram ID
        manager_id = None
        for mid, mdata in MANAGERS.items():
            if mdata['telegram_id'] == user_id:
                manager_id = mid
                break

        if not manager_id:
            await callback.answer("❌ Вы не зарегистрированы как менеджер в системе.", show_alert=True)
            return

        # Получить объявление из БД
        session = get_session()
        try:
            announcement = session.query(Announcement).filter(
                Announcement.id == announcement_id,
                Announcement.manager_id == manager_id,
                Announcement.status == 'pending'
            ).first()

            if not announcement:
                await callback.answer("❌ Объявление не найдено или уже обработано.", show_alert=True)
                return

            # Подготовить данные объявления для отправки
            from bot.messages import format_announcement_message
            announcement_data = {
                'announcement_number': announcement.announcement_number,
                'announcement_url': announcement.announcement_url,
                'organization_name': announcement.organization_name,
                'organization_bin': announcement.organization_bin,
                'legal_address': announcement.legal_address,
                'region': announcement.region,
                'lot_name': announcement.lot_name,
                'lot_description': announcement.lot_description,
                'keyword_matched': announcement.keyword_matched,
                'manager_id': announcement.manager_id,
                'manager_name': announcement.manager_name,
                'application_deadline': announcement.application_deadline,
                'procurement_method': announcement.procurement_method,
                'lots': announcement.lots
            }

            # Форматировать сообщение и добавить кнопки "Беру в работу" и "Отклонить"
            message_text = format_announcement_message(announcement_data, for_manager=True)
            keyboard = get_announcement_keyboard(announcement.id)

            # Отправить новое сообщение с объявлением через bot
            await bot.send_message(
                chat_id=callback.from_user.id,
                text=message_text,
                parse_mode='HTML',
                reply_markup=keyboard,
                disable_web_page_preview=True
            )

            await callback.answer()

        finally:
            session.close()

    except Exception as e:
        print(f"❌ Ошибка в callback_pending_view: {e}")
        await callback.answer("❌ Произошла ошибка при загрузке объявления.", show_alert=True)


@router.callback_query(F.data.startswith("postpone_"))
async def callback_postpone(callback: CallbackQuery):
    """Обработчик кнопки 'Отложить' - удаляет сообщение"""
    try:
        await callback.message.delete()
        await callback.answer("Объявление отложено")
    except Exception as e:
        print(f"❌ Ошибка при удалении сообщения: {e}")
        await callback.answer("Объявление отложено", show_alert=False)


@router.callback_query(F.data.startswith("claim_almaty_"))
async def callback_claim_almaty(callback: CallbackQuery):
    """Обработчик кнопки 'Мой район' для объявлений из Алматы"""
    try:
        user_id = callback.from_user.id

        # Извлечь announcement_id из callback_data
        announcement_id = int(callback.data.split("_")[-1])

        # Найти менеджера по telegram_id
        manager_id = None
        manager_name = None
        for mid, mdata in MANAGERS.items():
            if mdata['telegram_id'] == user_id:
                manager_id = mid
                manager_name = mdata['name']
                break

        if not manager_id:
            await callback.answer("❌ Вы не зарегистрированы как менеджер", show_alert=True)
            return

        # Получить объявление из БД
        session = get_session()
        try:
            announcement = session.query(Announcement).filter(
                Announcement.id == announcement_id
            ).first()

            if not announcement:
                await callback.answer("❌ Объявление не найдено", show_alert=True)
                return

            # Проверить, не забрано ли уже объявление
            if announcement.manager_id is not None:
                await callback.answer("❌ Это объявление уже забрал другой менеджер", show_alert=True)
                return

            # Установить manager_id
            announcement.manager_id = manager_id
            announcement.manager_name = manager_name
            session.commit()

            print(f"✅ Объявление {announcement.announcement_number} забрал менеджер {manager_name}")

        finally:
            session.close()

        # Изменить клавиатуру на обычную
        keyboard = get_announcement_keyboard(announcement_id)
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer(f"✅ Объявление назначено вам")

        # Уведомить других менеджеров из Алматы (1, 3, 4)
        almaty_managers = [1, 3, 4]
        bot = callback.bot

        for mid in almaty_managers:
            if mid == manager_id:
                continue  # Пропустить текущего менеджера

            other_telegram_id = MANAGERS[mid]['telegram_id']
            if not other_telegram_id:
                continue

            try:
                notification_text = (
                    f"📍 <b>Объявление из Алматы забрано</b>\n\n"
                    f"Менеджер <b>{manager_name}</b> забрал объявление:\n"
                    f"📋 {announcement.announcement_number}\n\n"
                    f"🔗 <a href='{announcement.announcement_url}'>Ссылка на объявление</a>"
                )
                await bot.send_message(
                    chat_id=other_telegram_id,
                    text=notification_text,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
                print(f"✅ Уведомление отправлено менеджеру {MANAGERS[mid]['name']}")
            except Exception as e:
                print(f"❌ Ошибка отправки уведомления менеджеру {MANAGERS[mid]['name']}: {e}")

    except Exception as e:
        print(f"❌ Ошибка в callback_claim_almaty: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.message(F.text.in_(["👤 Олеся", "👤 Анастасия", "👤 Жасулан", "👤 Алибек"]))
async def button_manager(message: Message):
    """Обработчик кнопок менеджеров для админа"""
    try:
        user_id = message.from_user.id

        # Проверка прав администратора
        if ADMIN_TELEGRAM_ID and str(user_id) != str(ADMIN_TELEGRAM_ID):
            await message.answer("❌ У вас нет прав для выполнения этой команды.")
            return

        # Извлечь имя менеджера из текста кнопки (убрать эмодзи)
        manager_name = message.text.replace("👤 ", "").strip()

        # Найти manager_id по имени
        manager_id = None
        for mid, mdata in MANAGERS.items():
            if mdata['name'] == manager_name:
                manager_id = mid
                break

        if not manager_id:
            await message.answer("❌ Менеджер не найден.")
            return

        # Показать главное меню менеджера
        text = format_manager_menu(manager_name)
        keyboard = get_manager_menu_keyboard(manager_id)

        await message.answer(text, parse_mode='HTML', reply_markup=keyboard)

    except Exception as e:
        print(f"❌ Ошибка в button_manager: {e}")
        await message.answer("❌ Произошла ошибка при загрузке данных менеджера.")


@router.callback_query(F.data.regexp(r"^manager_\d+_stats$"))
async def callback_manager_stats(callback: CallbackQuery):
    """Обработчик кнопки 'Статистика' менеджера"""
    try:
        user_id = callback.from_user.id

        # Проверка прав администратора
        if ADMIN_TELEGRAM_ID and str(user_id) != str(ADMIN_TELEGRAM_ID):
            await callback.answer("❌ Нет прав", show_alert=True)
            return

        # Извлечь manager_id из callback.data (manager_1_stats -> 1)
        parts = callback.data.split("_")
        manager_id = int(parts[1])

        # Получить имя менеджера
        manager_name = MANAGERS.get(manager_id, {}).get('name', 'Неизвестный')

        # Получить статистику
        stats = AnnouncementCRUD.get_manager_statistics(manager_id)

        # Форматировать сообщение
        text = format_manager_statistics(manager_name, stats)
        keyboard = get_manager_back_keyboard(manager_id)

        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        print(f"❌ Ошибка в callback_manager_stats: {e}")
        await callback.answer("❌ Произошла ошибка при загрузке статистики.", show_alert=True)


@router.callback_query(F.data.regexp(r"^manager_\d+_problems$"))
async def callback_manager_problems(callback: CallbackQuery):
    """Обработчик кнопки 'Проблемные' менеджера"""
    try:
        user_id = callback.from_user.id

        # Проверка прав администратора
        if ADMIN_TELEGRAM_ID and str(user_id) != str(ADMIN_TELEGRAM_ID):
            await callback.answer("❌ Нет прав", show_alert=True)
            return

        # Извлечь manager_id из callback.data
        parts = callback.data.split("_")
        manager_id = int(parts[1])

        # Получить имя менеджера
        manager_name = MANAGERS.get(manager_id, {}).get('name', 'Неизвестный')

        # Получить проблемные объявления
        problems = AnnouncementCRUD.get_problem_announcements(manager_id)

        # Форматировать сообщение
        text = format_problem_announcements(manager_name, problems)
        keyboard = get_problem_announcements_keyboard(manager_id, problems)

        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        print(f"❌ Ошибка в callback_manager_problems: {e}")
        await callback.answer("❌ Произошла ошибка при загрузке проблемных объявлений.", show_alert=True)


@router.callback_query(F.data.regexp(r"^manager_\d+_active$"))
async def callback_manager_active(callback: CallbackQuery):
    """Обработчик кнопки 'Активные' менеджера"""
    try:
        user_id = callback.from_user.id

        # Проверка прав администратора
        if ADMIN_TELEGRAM_ID and str(user_id) != str(ADMIN_TELEGRAM_ID):
            await callback.answer("❌ Нет прав", show_alert=True)
            return

        # Извлечь manager_id из callback.data
        parts = callback.data.split("_")
        manager_id = int(parts[1])

        # Получить имя менеджера
        manager_name = MANAGERS.get(manager_id, {}).get('name', 'Неизвестный')

        # Получить активные объявления
        active = AnnouncementCRUD.get_active_announcements(manager_id)

        # Форматировать сообщение
        text = format_active_announcements(manager_name, active)
        keyboard = get_active_announcements_keyboard(manager_id, active)

        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        print(f"❌ Ошибка в callback_manager_active: {e}")
        await callback.answer("❌ Произошла ошибка при загрузке активных объявлений.", show_alert=True)


@router.callback_query(F.data.regexp(r"^manager_\d+_actions$"))
async def callback_manager_actions(callback: CallbackQuery):
    """Обработчик кнопки 'Действия' менеджера"""
    try:
        user_id = callback.from_user.id

        # Проверка прав администратора
        if ADMIN_TELEGRAM_ID and str(user_id) != str(ADMIN_TELEGRAM_ID):
            await callback.answer("❌ Нет прав", show_alert=True)
            return

        # Извлечь manager_id из callback.data
        parts = callback.data.split("_")
        manager_id = int(parts[1])

        # Получить имя менеджера
        manager_name = MANAGERS.get(manager_id, {}).get('name', 'Неизвестный')

        # Получить последние действия менеджера
        actions = ManagerActionCRUD.get_by_manager(manager_id, limit=20)

        # Форматировать сообщение
        text = format_manager_actions(manager_name, actions)
        keyboard = get_manager_back_keyboard(manager_id)

        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        print(f"❌ Ошибка в callback_manager_actions: {e}")
        await callback.answer("❌ Произошла ошибка при загрузке действий менеджера.", show_alert=True)


@router.callback_query(F.data.regexp(r"^manager_\d+_view_\d+$"))
async def callback_manager_view_announcement(callback: CallbackQuery):
    """Обработчик просмотра объявления из списка менеджера"""
    try:
        user_id = callback.from_user.id

        # Проверка прав администратора
        if ADMIN_TELEGRAM_ID and str(user_id) != str(ADMIN_TELEGRAM_ID):
            await callback.answer("❌ Нет прав", show_alert=True)
            return

        # Извлечь manager_id и announcement_id из callback.data (manager_1_view_123)
        parts = callback.data.split("_")
        manager_id = int(parts[1])
        announcement_id = int(parts[3])

        session = get_session()
        try:
            # Получить объявление из базы данных
            announcement = session.query(Announcement).filter(
                Announcement.id == announcement_id
            ).first()

            if not announcement:
                await callback.answer("❌ Объявление не найдено.", show_alert=True)
                return

            # Подготовить данные объявления для отправки
            from bot.messages import format_announcement_details
            announcement_data = {
                'announcement_number': announcement.announcement_number,
                'announcement_url': announcement.announcement_url,
                'organization_name': announcement.organization_name,
                'organization_bin': announcement.organization_bin,
                'legal_address': announcement.legal_address,
                'region': announcement.region,
                'lot_name': announcement.lot_name,
                'lot_description': announcement.lot_description,
                'keyword_matched': announcement.keyword_matched,
                'manager_id': announcement.manager_id,
                'manager_name': announcement.manager_name,
                'status': announcement.status,
                'is_processed': announcement.is_processed,
                'created_at': announcement.created_at,
                'response_at': announcement.response_at,
                'rejection_reason': announcement.rejection_reason
            }

            # Форматировать детали объявления
            text = format_announcement_details(announcement_data)
            keyboard = get_announcement_detail_keyboard(manager_id, announcement_id)

            await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard, disable_web_page_preview=True)
            await callback.answer()

        finally:
            session.close()

    except Exception as e:
        print(f"❌ Ошибка в callback_manager_view_announcement: {e}")
        await callback.answer("❌ Произошла ошибка при загрузке объявления.", show_alert=True)


@router.callback_query(F.data.regexp(r"^manager_\d+_back$"))
async def callback_manager_back(callback: CallbackQuery):
    """Обработчик кнопки 'Назад' - возврат к меню менеджера"""
    try:
        user_id = callback.from_user.id

        # Проверка прав администратора
        if ADMIN_TELEGRAM_ID and str(user_id) != str(ADMIN_TELEGRAM_ID):
            await callback.answer("❌ Нет прав", show_alert=True)
            return

        # Извлечь manager_id из callback.data
        parts = callback.data.split("_")
        manager_id = int(parts[1])

        # Получить имя менеджера
        manager_name = MANAGERS.get(manager_id, {}).get('name', 'Неизвестный')

        # Показать главное меню менеджера
        text = format_manager_menu(manager_name)
        keyboard = get_manager_menu_keyboard(manager_id)

        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        print(f"❌ Ошибка в callback_manager_back: {e}")
        await callback.answer("❌ Произошла ошибка.", show_alert=True)


# ==================== Обработчики для координатора ====================

@router.message(F.text == "📋 Объявления в работе")
async def button_coordinator_work_announcements(message: Message):
    """Обработчик кнопки 'Объявления в работе' для координатора"""
    user_id = message.from_user.id

    # Проверка, является ли пользователь координатором
    is_coordinator = COORDINATOR_TELEGRAM_ID and str(user_id) == str(COORDINATOR_TELEGRAM_ID)

    if not is_coordinator:
        # Это может быть менеджер, который нажал ту же кнопку
        # Вызываем обработчик для менеджера
        return await button_work_announcements(message)

    # Получить объявления со статусом accepted и действующим дедлайном
    announcements = AnnouncementCRUD.get_accepted_with_valid_deadline()

    # Форматировать сообщение
    text = format_coordinator_announcements_list(announcements)

    # Получить клавиатуру
    keyboard = get_coordinator_announcements_keyboard(announcements)

    await message.answer(text, parse_mode='HTML', reply_markup=keyboard)


@router.callback_query(F.data.startswith("coord_view_"))
async def callback_coordinator_view_announcement(callback: CallbackQuery):
    """Обработчик просмотра объявления координатором"""
    try:
        user_id = callback.from_user.id

        # Проверка прав координатора
        is_coordinator = COORDINATOR_TELEGRAM_ID and str(user_id) == str(COORDINATOR_TELEGRAM_ID)

        if not is_coordinator:
            await callback.answer("❌ Нет прав", show_alert=True)
            return

        # Извлечь announcement_id из callback.data (coord_view_123)
        announcement_id = int(callback.data.split("_")[2])

        session = get_session()
        try:
            # Получить объявление из базы данных
            announcement = session.query(Announcement).filter(
                Announcement.id == announcement_id
            ).first()

            if not announcement:
                await callback.answer("❌ Объявление не найдено.", show_alert=True)
                return

            # Получить имя менеджера
            manager_name = announcement.manager_name or "Неизвестный"

            # Форматировать детали объявления для координатора
            text = format_coordinator_announcement_details(announcement, manager_name)
            keyboard = get_coordinator_announcement_detail_keyboard()

            await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard, disable_web_page_preview=True)
            await callback.answer()

        finally:
            session.close()

    except Exception as e:
        print(f"❌ Ошибка в callback_coordinator_view_announcement: {e}")
        await callback.answer("❌ Произошла ошибка при загрузке объявления.", show_alert=True)


@router.callback_query(F.data == "coord_back_to_list")
async def callback_coordinator_back_to_list(callback: CallbackQuery):
    """Обработчик кнопки 'Назад к списку' для координатора"""
    try:
        user_id = callback.from_user.id

        # Проверка прав координатора
        is_coordinator = COORDINATOR_TELEGRAM_ID and str(user_id) == str(COORDINATOR_TELEGRAM_ID)

        if not is_coordinator:
            await callback.answer("❌ Нет прав", show_alert=True)
            return

        # Получить объявления со статусом accepted и действующим дедлайном
        announcements = AnnouncementCRUD.get_accepted_with_valid_deadline()

        # Форматировать сообщение
        text = format_coordinator_announcements_list(announcements)

        # Получить клавиатуру
        keyboard = get_coordinator_announcements_keyboard(announcements)

        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        print(f"❌ Ошибка в callback_coordinator_back_to_list: {e}")
        await callback.answer("❌ Произошла ошибка.", show_alert=True)


def get_dispatcher() -> Dispatcher:
    """Создать и настроить диспетчер"""
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    return dp

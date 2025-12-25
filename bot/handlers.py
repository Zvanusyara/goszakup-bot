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

from database.crud import AnnouncementCRUD, ManagerActionCRUD
from database.models import get_session, Announcement
from bot.messages import (
    START_MESSAGE,
    HELP_MESSAGE,
    format_accepted_notification,
    format_rejected_notification,
    format_stats_message
)
from config import TELEGRAM_BOT_TOKEN, ADMIN_TELEGRAM_ID, MANAGERS
from sqlalchemy import func

router = Router()


# FSM для получения причины отказа
class RejectionState(StatesGroup):
    waiting_for_reason = State()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.answer(START_MESSAGE, parse_mode='HTML')


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    await message.answer(HELP_MESSAGE, parse_mode='HTML')


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

        await message.answer(format_stats_message(stats), parse_mode='HTML')

    finally:
        session.close()


@router.callback_query(F.data.startswith("accept_"))
async def callback_accept(callback: CallbackQuery, bot: Bot):
    """Обработчик нажатия кнопки 'Принять'"""
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

    # Получить данные объявления для уведомления админа
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


def get_dispatcher() -> Dispatcher:
    """Создать и настроить диспетчер"""
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    return dp

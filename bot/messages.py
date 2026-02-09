"""
Шаблоны сообщений для Telegram бота
"""
from datetime import datetime


def ensure_datetime(date_value):
    """
    Преобразует строку в datetime если нужно (для совместимости с SQLite)

    Args:
        date_value: datetime объект или строка в ISO формате

    Returns:
        datetime объект или None
    """
    if date_value is None:
        return None
    if isinstance(date_value, datetime):
        return date_value
    if isinstance(date_value, str):
        try:
            # SQLite хранит в ISO формате
            return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
        except:
            return None
    return None


def format_announcement_message(announcement: dict, for_manager: bool = True) -> str:
    """
    Форматирование сообщения об объявлении

    Args:
        announcement: Данные объявления (dict или объект Announcement)
        for_manager: True если сообщение для менеджера, False для админа

    Returns:
        Отформатированное сообщение
    """
    import json

    # Поддержка как dict, так и объекта Announcement
    def get_value(key, default='N/A'):
        if isinstance(announcement, dict):
            value = announcement.get(key, default)
        else:
            value = getattr(announcement, key, default)
        # Если значение None, вернуть default
        return value if value is not None else default

    # Форматируем дату окончания приема заявок
    # ВАЖНО: application_deadline уже приходит в местном времени Казахстана из API
    deadline = get_value('application_deadline')
    deadline = ensure_datetime(deadline)
    if deadline:
        deadline_str = deadline.strftime('%d.%m.%Y %H:%M')
    else:
        deadline_str = 'Не указан'

    # Способ закупки
    procurement_method = get_value('procurement_method', 'Не указан')

    # Получаем данные лотов
    lots_data = get_value('lots', None)

    # Если lots - строка JSON, десериализуем
    if lots_data and isinstance(lots_data, str):
        try:
            lots_data = json.loads(lots_data)
        except:
            lots_data = None

    # Форматируем секцию лотов
    if lots_data and isinstance(lots_data, list) and len(lots_data) > 0:
        # Несколько лотов
        lots_section = f"📦 <b>Подходящих лотов в объявлении:</b> {len(lots_data)}\n\n"
        for i, lot in enumerate(lots_data, 1):
            lot_number = lot.get('number')  # Реальный номер лота
            lot_name = lot.get('name', 'N/A')
            lot_desc = lot.get('description', '')
            lot_keyword = lot.get('keyword', 'N/A')

            # Ограничиваем длину описания
            if lot_desc and len(lot_desc) > 150:
                lot_desc = lot_desc[:150] + "..."

            # Используем реальный номер лота если есть, иначе порядковый
            lot_display = f"№{lot_number}" if lot_number else f"{i}"
            lots_section += f"📦 <b>ЛОТ {lot_display}</b>\n"
            lots_section += f"💼 <b>Название:</b> {lot_name}\n"
            if lot_desc:
                lots_section += f"📝 <b>Описание:</b> {lot_desc}\n"
            lots_section += f"🏷️ <b>Ключевое слово:</b> {lot_keyword}\n\n"
    else:
        # Старый формат - один лот
        lot_name = get_value('lot_name', 'N/A')
        keyword = get_value('keyword_matched', 'N/A')
        lots_section = (
            f"💼 <b>Лот:</b> {lot_name}\n"
            f"🏷️ <b>Ключевое слово:</b> {keyword}\n"
        )

    if for_manager:
        message = (
            f"🔔 <b>Новое объявление</b>\n\n"
            f"📋 <b>Номер:</b> {get_value('announcement_number')}\n"
            f"📍 <b>Регион:</b> {get_value('region')}\n"
            f"🏢 <b>Организация:</b> {get_value('organization_name')}\n"
            f"📫 <b>Юридический адрес:</b> {get_value('legal_address')}\n\n"
            f"{lots_section}"
            f"📦 <b>Способ закупки:</b> {procurement_method}\n"
            f"⏰ <b>Срок окончания приема заявок:</b> {deadline_str}\n\n"
            f"🔗 <a href='{get_value('announcement_url', '#')}'>Открыть объявление</a>"
        )
    else:
        # Для админа добавляем информацию о менеджере
        message = (
            f"📬 <b>Новое объявление распределено</b>\n\n"
            f"👤 <b>Менеджер:</b> {get_value('manager_name')}\n\n"
            f"📋 <b>Номер:</b> {get_value('announcement_number')}\n"
            f"📍 <b>Регион:</b> {get_value('region')}\n"
            f"🏢 <b>Организация:</b> {get_value('organization_name')}\n"
            f"📫 <b>Юридический адрес:</b> {get_value('legal_address')}\n\n"
            f"{lots_section}"
            f"📦 <b>Способ закупки:</b> {procurement_method}\n"
            f"⏰ <b>Срок окончания приема заявок:</b> {deadline_str}\n\n"
            f"🔗 <a href='{get_value('announcement_url', '#')}'>Открыть объявление</a>"
        )

    return message


def format_accepted_notification(announcement_number: str, manager_name: str) -> str:
    """Уведомление админу о принятии объявления"""
    return (
        f"✅ <b>Объявление принято</b>\n\n"
        f"👤 <b>Менеджер:</b> {manager_name}\n"
        f"📋 <b>Номер объявления:</b> {announcement_number}"
    )


def format_rejected_notification(announcement_number: str, manager_name: str, reason: str) -> str:
    """Уведомление админу об отклонении объявления"""
    return (
        f"❌ <b>Объявление отклонено</b>\n\n"
        f"👤 <b>Менеджер:</b> {manager_name}\n"
        f"📋 <b>Номер объявления:</b> {announcement_number}\n\n"
        f"📝 <b>Причина:</b> {reason}"
    )


def format_coordinator_notification(announcement_number: str, announcement_url: str,
                                    manager_name: str, application_deadline) -> str:
    """
    Уведомление координатору о принятом менеджером объявлении

    Args:
        announcement_number: Номер объявления
        announcement_url: Ссылка на объявление
        manager_name: Имя менеджера, который принял объявление
        application_deadline: Срок окончания приема заявок (datetime или None)

    Returns:
        Отформатированное сообщение
    """
    # Форматируем дату окончания приема заявок
    # ВАЖНО: application_deadline уже приходит в местном времени Казахстана из API
    application_deadline = ensure_datetime(application_deadline)
    if application_deadline:
        deadline_str = application_deadline.strftime('%d.%m.%Y %H:%M')
    else:
        deadline_str = 'Не указан'

    return (
        f"✅ <b>Объявление принято менеджером</b>\n\n"
        f"👤 <b>Менеджер:</b> {manager_name}\n"
        f"📋 <b>Номер объявления:</b> {announcement_number}\n"
        f"⏰ <b>Срок окончания приема заявок:</b> {deadline_str}\n\n"
        f"🔗 <a href='{announcement_url}'>Открыть объявление</a>"
    )


def format_stats_message(stats: dict) -> str:
    """Форматирование статистики"""
    return (
        f"📊 <b>Статистика</b>\n\n"
        f"📥 Всего объявлений: {stats.get('total', 0)}\n"
        f"⏳ Ожидают ответа: {stats.get('pending', 0)}\n"
        f"✅ Принято: {stats.get('accepted', 0)}\n"
        f"❌ Отклонено: {stats.get('rejected', 0)}"
    )


def format_admin_dashboard(dashboard_data: dict) -> str:
    """
    Форматирование главного дашборда администратора

    Args:
        dashboard_data: Данные для дашборда со статистикой

    Returns:
        Отформатированное сообщение дашборда
    """
    from datetime import datetime

    # Текущая дата и время
    now = datetime.now()
    current_date = now.strftime("%d.%m.%Y")
    current_time = now.strftime("%H:%M")

    # Данные объявлений
    new = dashboard_data.get('new', 0)
    in_progress = dashboard_data.get('in_progress', 0)
    processed = dashboard_data.get('processed', 0)
    rejected = dashboard_data.get('rejected', 0)
    total_today = dashboard_data.get('total_today', 0)

    # Критические зоны
    stuck_24h = dashboard_data.get('stuck_24h', 0)
    no_response_2h = dashboard_data.get('no_response_2h', 0)
    needs_attention = dashboard_data.get('needs_attention', 0)

    message = (
        f"═══════════════════════════\n"
        f"👔 <b>АДМИН-ПАНЕЛЬ</b>\n"
        f"═══════════════════════════\n\n"
        f"📅 Сегодня: {current_date}\n"
        f"⏰ Обновлено: {current_time}\n\n"

        f"📊 <b>ОБЪЯВЛЕНИЯ</b>\n\n"
        f"🆕 Новые: <b>{new}</b>\n"
        f"⏳ В работе: <b>{in_progress}</b>\n"
        f"✅ Обработаны: <b>{processed}</b>\n"
        f"❌ Отклонены: <b>{rejected}</b>\n\n"
        f"📈 Всего за день: <b>{total_today}</b>\n\n"

        f"⚡ <b>КРИТИЧЕСКИЕ ЗОНЫ</b>\n\n"
        f"🔴 Зависли &gt;24ч: <b>{stuck_24h}</b>\n"
        f"🟡 Без ответа &gt;2ч: <b>{no_response_2h}</b>\n"
        f"⚠️ Нужно внимание: <b>{needs_attention}</b>"
    )

    return message


START_MESSAGE = """
👋 Добро пожаловать в систему мониторинга госзакупок!

Этот бот автоматически отправляет уведомления о новых объявлениях на портале goszakup.gov.kz.

<b>Ваши действия:</b>
• При получении объявления нажмите <b>"Беру в работу"</b> для работы с ним
• Нажмите <b>"Отклонить"</b> и укажите причину отказа
• Используйте кнопки внизу для быстрого доступа к функциям

<b>Кнопки меню:</b>
📋 Объявления в работе - Список ваших принятых объявлений
📊 Статистика - Ваша статистика по обработке
ℹ️ Справка - Подробная информация о боте

Удачи в работе!
"""

HELP_MESSAGE = """
ℹ️ <b>Справка по использованию бота</b>

<b>Как работает система:</b>
1. Бот автоматически парсит портал goszakup.gov.kz
2. Находит объявления по вашим ключевым словам и региону
3. Отправляет вам уведомления о подходящих объявлениях

<b>Что делать при получении уведомления:</b>
• Ознакомьтесь с деталями объявления
• Перейдите по ссылке для просмотра на портале
• Нажмите "✅ Беру в работу" если готовы работать с объявлением
• Нажмите "❌ Отклонить" и укажите причину, если объявление не подходит

<b>Работа с принятыми объявлениями:</b>
• Нажмите кнопку "📋 Объявления в работе" для просмотра списка
• Выберите объявление для просмотра деталей
• Нажмите "✅ Обработал" когда завершите работу с объявлением
• Нажмите "📋 Подробности" для просмотра полной информации

<b>Кнопки меню:</b>
📋 Объявления в работе - Ваши принятые объявления
📊 Статистика - Статистика по обработке
ℹ️ Справка - Эта справка
👔 Админ-панель - Для администратора

По вопросам обращайтесь к администратору.
"""


def format_work_announcements_list(announcements: list) -> str:
    """
    Форматирование списка объявлений в работе

    Args:
        announcements: Список объявлений

    Returns:
        Отформатированное сообщение
    """
    if not announcements:
        return (
            "📋 <b>Объявления в работе</b>\n\n"
            "У вас пока нет принятых объявлений в работе."
        )

    message = f"📋 <b>Объявления в работе</b> ({len(announcements)})\n\n"
    message += "Выберите объявление для просмотра:\n\n"

    return message


def format_pending_announcements_list(announcements: list) -> str:
    """
    Форматирование списка не принятых объявлений

    Args:
        announcements: Список объявлений

    Returns:
        Отформатированное сообщение
    """
    if not announcements:
        return (
            "🔔 <b>Не принятые объявления</b>\n\n"
            "У вас нет не принятых объявлений."
        )

    message = f"🔔 <b>Не принятые объявления</b> ({len(announcements)})\n\n"
    message += "Выберите объявление для просмотра:\n\n"

    return message


def format_announcement_details(announcement) -> str:
    """
    Форматирование подробной информации об объявлении

    Args:
        announcement: Объект объявления из БД

    Returns:
        Отформатированное сообщение
    """
    # Используем ту же логику, что и при первой отправке
    message = format_announcement_message(announcement, for_manager=True)

    # Заменяем заголовок и добавляем статус
    message = message.replace("🔔 <b>Новое объявление</b>",
                             f"{'✅' if announcement.is_processed else '📄'} <b>Подробности объявления</b>")

    # Добавляем статус обработки в конце
    if announcement.is_processed:
        message += "\n\n✅ <b>Статус:</b> Обработано"
    else:
        message += "\n\n⏳ <b>Статус:</b> В работе"

    return message


def format_manager_menu(manager_name: str) -> str:
    """
    Форматирование главного меню менеджера для админа

    Args:
        manager_name: Имя менеджера

    Returns:
        Отформатированное сообщение
    """
    return (
        f"👤 <b>{manager_name}</b>\n\n"
        f"Выберите раздел:"
    )


def format_manager_statistics(manager_name: str, stats: dict) -> str:
    """
    Форматирование статистики менеджера

    Args:
        manager_name: Имя менеджера
        stats: Словарь со статистикой

    Returns:
        Отформатированное сообщение
    """
    return (
        f"📊 <b>Статистика: {manager_name}</b>\n\n"

        f"📈 <b>ОБЪЯВЛЕНИЯ</b>\n"
        f"📥 Всего объявлений: <b>{stats['total']}</b>\n"
        f"⏳ В ожидании: <b>{stats['pending']}</b>\n"
        f"✅ Принято: <b>{stats['accepted']}</b>\n"
        f"🔄 Обработано: <b>{stats['processed']}</b>\n"
        f"❌ Отклонено: <b>{stats['rejected']}</b>\n\n"

        f"📊 <b>ЭФФЕКТИВНОСТЬ</b>\n"
        f"✅ Процент принятия: <b>{stats['acceptance_rate']}%</b>\n"
        f"🔄 Процент обработки: <b>{stats['processing_rate']}%</b>\n"
        f"⏱ Среднее время реакции: <b>{stats['avg_response_time']} ч</b>"
    )


def format_problem_announcements(manager_name: str, problems: dict) -> str:
    """
    Форматирование проблемных объявлений менеджера

    Args:
        manager_name: Имя менеджера
        problems: Словарь с проблемными объявлениями

    Returns:
        Отформатированное сообщение
    """
    from datetime import datetime, timezone

    pending_24h = problems['pending_24h']
    accepted_48h = problems['accepted_48h']

    total_problems = len(pending_24h) + len(accepted_48h)

    message = (
        f"⚠️ <b>Проблемные объявления: {manager_name}</b>\n\n"
    )

    if total_problems == 0:
        message += "✅ Нет проблемных объявлений!"
        return message

    if pending_24h:
        message += f"🔴 <b>Pending &gt;24ч ({len(pending_24h)})</b>\n"
        for ann in pending_24h[:5]:  # Показываем первые 5
            created_at = ensure_datetime(ann.created_at)
            if created_at:
                hours_ago = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
                message += f"• {ann.announcement_number[:15]}... ({int(hours_ago)}ч)\n"
            else:
                message += f"• {ann.announcement_number[:15]}...\n"
        if len(pending_24h) > 5:
            message += f"... и еще {len(pending_24h) - 5}\n"
        message += "\n"

    if accepted_48h:
        message += f"🟡 <b>Accepted не обработаны &gt;48ч ({len(accepted_48h)})</b>\n"
        for ann in accepted_48h[:5]:  # Показываем первые 5
            response_at = ensure_datetime(ann.response_at)
            if response_at:
                hours_ago = (datetime.now(timezone.utc) - response_at).total_seconds() / 3600
                message += f"• {ann.announcement_number[:15]}... ({int(hours_ago)}ч)\n"
            else:
                message += f"• {ann.announcement_number[:15]}...\n"
        if len(accepted_48h) > 5:
            message += f"... и еще {len(accepted_48h) - 5}\n"

    message += "\n💡 Нажмите на объявление для просмотра деталей"

    return message


def format_active_announcements(manager_name: str, active: list) -> str:
    """
    Форматирование активных объявлений менеджера

    Args:
        manager_name: Имя менеджера
        active: Список активных объявлений

    Returns:
        Отформатированное сообщение
    """
    message = (
        f"📋 <b>Активные объявления: {manager_name}</b>\n\n"
    )

    if not active:
        message += "✅ Нет активных объявлений!"
        return message

    message += f"Всего: <b>{len(active)}</b>\n\n"

    # Группировка по датам
    from collections import defaultdict
    by_date = defaultdict(list)

    for ann in active:
        created_at = ensure_datetime(ann.created_at)
        date_str = created_at.strftime('%d.%m.%Y') if created_at else 'N/A'
        by_date[date_str].append(ann)

    # Показываем первые 10 объявлений
    count = 0
    for date_str in sorted(by_date.keys(), reverse=True):
        if count >= 10:
            break
        message += f"📅 <b>{date_str}</b>\n"
        for ann in by_date[date_str]:
            if count >= 10:
                break
            message += f"• {ann.announcement_number[:20]}...\n"
            count += 1
        message += "\n"

    if len(active) > 10:
        message += f"... и еще {len(active) - 10} объявлений\n\n"

    message += "💡 Нажмите на объявление для просмотра деталей"

    return message


def format_manager_actions(manager_name: str, actions: list) -> str:
    """
    Форматирование истории действий менеджера

    Args:
        manager_name: Имя менеджера
        actions: Список действий

    Returns:
        Отформатированное сообщение
    """
    message = (
        f"📝 <b>Последние действия: {manager_name}</b>\n\n"
    )

    if not actions:
        message += "Нет записей о действиях"
        return message

    message += f"Всего записей: <b>{len(actions)}</b>\n\n"

    # Эмодзи для действий
    action_emoji = {
        'accepted': '✅',
        'rejected': '❌',
        'processed': '🔄',
        'viewed': '👁'
    }

    # Показываем действия
    for action in actions[:15]:  # Первые 15 действий
        emoji = action_emoji.get(action.action, '📌')
        created_at = ensure_datetime(action.created_at)
        time_str = created_at.strftime('%d.%m %H:%M') if created_at else 'N/A'

        # Получить номер объявления
        announcement_number = "N/A"
        if action.announcement:
            announcement_number = action.announcement.announcement_number[:15]

        message += f"{emoji} <code>{time_str}</code> - {action.action}\n"
        message += f"   📋 {announcement_number}...\n"

        if action.comment:
            comment_short = action.comment[:50] + "..." if len(action.comment) > 50 else action.comment
            message += f"   💬 {comment_short}\n"

        message += "\n"

    if len(actions) > 15:
        message += f"... и еще {len(actions) - 15} действий"

    return message


def format_deadline_reminder(announcement, hours_left: int) -> str:
    """
    Форматирование напоминания о приближающемся дедлайне

    Args:
        announcement: Объект объявления из БД
        hours_left: Часов до окончания срока (48, 24, 2)

    Returns:
        Отформатированное сообщение
    """
    # Определить эмодзи в зависимости от срочности
    if hours_left <= 2:
        urgency_emoji = "🚨"
        urgency_text = "СРОЧНО!"
    elif hours_left <= 24:
        urgency_emoji = "⚠️"
        urgency_text = "ВНИМАНИЕ!"
    else:
        urgency_emoji = "⏰"
        urgency_text = "Напоминание"

    # Форматировать дату дедлайна
    deadline = ensure_datetime(announcement.application_deadline)
    deadline_str = deadline.strftime("%d.%m.%Y %H:%M") if deadline else 'Не указан'

    message = f"{urgency_emoji} <b>{urgency_text}</b>\n\n"
    message += f"До окончания срока подачи заявок осталось <b>{hours_left} ч</b>\n\n"
    message += f"📋 <b>Объявление:</b>\n"
    message += f"{announcement.announcement_number}\n\n"

    if announcement.lot_name:
        lot_name_short = announcement.lot_name[:100] + "..." if len(announcement.lot_name) > 100 else announcement.lot_name
        message += f"📦 <b>Лот:</b>\n{lot_name_short}\n\n"

    message += f"🏢 <b>Заказчик:</b>\n{announcement.organization_name}\n\n"
    message += f"📍 <b>Регион:</b> {announcement.region}\n\n"
    message += f"⏱ <b>Дедлайн:</b> {deadline_str}\n\n"
    message += f"🔗 <a href='{announcement.announcement_url}'>Открыть объявление</a>"

    return message


def format_coordinator_announcements_list(announcements: list) -> str:
    """
    Форматирование списка объявлений в работе для координатора

    Args:
        announcements: Список объявлений

    Returns:
        Отформатированное сообщение
    """
    if not announcements:
        return (
            "📋 <b>Объявления в работе</b>\n\n"
            "Нет объявлений в работе с действующим сроком."
        )

    message = f"📋 <b>Объявления в работе</b> ({len(announcements)})\n\n"
    message += "Выберите объявление для просмотра:\n\n"

    return message


def format_coordinator_announcement_details(announcement, manager_name: str) -> str:
    """
    Форматирование деталей объявления для координатора

    Args:
        announcement: Объект объявления из БД
        manager_name: Имя менеджера, работающего с объявлением

    Returns:
        Отформатированное сообщение
    """
    import json

    # Форматируем дату окончания приема заявок
    deadline = ensure_datetime(announcement.application_deadline)
    if deadline:
        deadline_str = deadline.strftime('%d.%m.%Y %H:%M')
    else:
        deadline_str = 'Не указан'

    # Способ закупки
    procurement_method = announcement.procurement_method or 'Не указан'

    # Получаем данные лотов
    lots_data = announcement.lots

    # Если lots - строка JSON, десериализуем
    if lots_data and isinstance(lots_data, str):
        try:
            lots_data = json.loads(lots_data)
        except:
            lots_data = None

    # Форматируем секцию лотов (короткая версия)
    if lots_data and isinstance(lots_data, list) and len(lots_data) > 0:
        lots_section = f"📦 <b>Лотов:</b> {len(lots_data)}\n"
        # Показываем только первый лот кратко
        first_lot = lots_data[0]
        lot_name = first_lot.get('name', 'N/A')
        if len(lot_name) > 80:
            lot_name = lot_name[:80] + "..."
        lots_section += f"💼 {lot_name}\n"
        if len(lots_data) > 1:
            lots_section += f"   ... и еще {len(lots_data) - 1}\n"
    else:
        # Старый формат
        lot_name = announcement.lot_name or 'N/A'
        if len(lot_name) > 80:
            lot_name = lot_name[:80] + "..."
        lots_section = f"💼 <b>Лот:</b> {lot_name}\n"

    message = (
        f"📋 <b>Объявление</b>\n\n"
        f"👤 <b>Менеджер:</b> {manager_name}\n\n"
        f"📋 <b>Номер:</b> {announcement.announcement_number}\n"
        f"📍 <b>Регион:</b> {announcement.region or 'N/A'}\n"
        f"🏢 <b>Организация:</b> {announcement.organization_name or 'N/A'}\n\n"
        f"{lots_section}\n"
        f"📦 <b>Способ закупки:</b> {procurement_method}\n"
        f"⏰ <b>Срок окончания приема заявок:</b> {deadline_str}\n\n"
        f"🔗 <a href='{announcement.announcement_url or '#'}'>Открыть объявление</a>"
    )

    return message


COORDINATOR_START_MESSAGE = """
👋 Добро пожаловать в систему мониторинга госзакупок!

<b>Вы - координатор</b>

Здесь вы можете отслеживать объявления, принятые менеджерами.

<b>Кнопка меню:</b>
📋 Объявления в работе - Список всех принятых объявлений со сроками

Удачи в работе!
"""

"""
Скрипт для просмотра данных из базы данных
"""
from database.models import init_database
from database.crud import AnnouncementCRUD, ManagerActionCRUD, ParsingLogCRUD
from datetime import datetime


def print_separator(title="", width=80):
    """Печать разделителя"""
    if title:
        print(f"\n{'=' * width}")
        print(f"{title.center(width)}")
        print(f"{'=' * width}\n")
    else:
        print("=" * width)


def view_announcements():
    """Просмотр всех объявлений"""
    announcements = AnnouncementCRUD.get_all_for_report()

    print_separator("📋 ОБЪЯВЛЕНИЯ В БАЗЕ ДАННЫХ")

    if not announcements:
        print("⚠️  База данных пустая. Запустите парсинг для добавления данных.")
        return

    print(f"Всего объявлений: {len(announcements)}\n")

    for i, ann in enumerate(announcements, 1):
        print(f"{'─' * 80}")
        print(f"#{i}. ОБЪЯВЛЕНИЕ {ann.announcement_number}")
        print(f"{'─' * 80}")
        print(f"📝 Название лота: {ann.lot_name}")
        print(f"🏢 Организация: {ann.organization_name}")
        print(f"🔢 БИН: {ann.organization_bin}")
        print(f"📍 Адрес: {ann.legal_address}")
        print(f"🌍 Регион: {ann.region}")
        print(f"🔑 Ключевое слово: {ann.keyword_matched}")
        print(f"👤 Менеджер: {ann.manager_name} (ID: {ann.manager_id})")

        # Статус с цветными эмодзи
        status_emoji = {
            'pending': '⏳',
            'accepted': '✅',
            'rejected': '❌'
        }
        print(f"📊 Статус: {status_emoji.get(ann.status, '❓')} {ann.status.upper()}")

        if ann.rejection_reason:
            print(f"💬 Причина отклонения: {ann.rejection_reason}")

        print(f"📅 Создано: {ann.created_at.strftime('%d.%m.%Y %H:%M')}")

        if ann.response_at:
            print(f"⏰ Ответ получен: {ann.response_at.strftime('%d.%m.%Y %H:%M')}")

        print(f"🔗 URL: {ann.announcement_url}")
        print()


def view_stats():
    """Просмотр статистики"""
    announcements = AnnouncementCRUD.get_all_for_report()

    print_separator("📊 СТАТИСТИКА")

    if not announcements:
        print("⚠️  Нет данных для статистики\n")
        return

    # Общая статистика
    total = len(announcements)
    pending = len([a for a in announcements if a.status == 'pending'])
    accepted = len([a for a in announcements if a.status == 'accepted'])
    rejected = len([a for a in announcements if a.status == 'rejected'])

    print(f"📈 Всего объявлений: {total}")
    print(f"⏳ Ожидают ответа: {pending}")
    print(f"✅ Принято: {accepted}")
    print(f"❌ Отклонено: {rejected}")
    print()

    # Статистика по менеджерам
    manager_stats = {}
    for ann in announcements:
        if ann.manager_id not in manager_stats:
            manager_stats[ann.manager_id] = {
                'name': ann.manager_name,
                'total': 0,
                'pending': 0,
                'accepted': 0,
                'rejected': 0
            }
        manager_stats[ann.manager_id]['total'] += 1
        manager_stats[ann.manager_id][ann.status] += 1

    print(f"{'─' * 80}")
    print("👥 СТАТИСТИКА ПО МЕНЕДЖЕРАМ:")
    print(f"{'─' * 80}")

    for manager_id, stats in manager_stats.items():
        print(f"\n👤 {stats['name']} (ID: {manager_id})")
        print(f"   Всего: {stats['total']}")
        print(f"   ⏳ Ожидают: {stats['pending']}")
        print(f"   ✅ Принято: {stats['accepted']}")
        print(f"   ❌ Отклонено: {stats['rejected']}")

    # Статистика по регионам
    print(f"\n{'─' * 80}")
    print("🌍 СТАТИСТИКА ПО РЕГИОНАМ:")
    print(f"{'─' * 80}\n")

    region_stats = {}
    for ann in announcements:
        if ann.region not in region_stats:
            region_stats[ann.region] = 0
        region_stats[ann.region] += 1

    for region, count in sorted(region_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"   {region}: {count}")

    # Статистика по ключевым словам
    print(f"\n{'─' * 80}")
    print("🔑 СТАТИСТИКА ПО КЛЮЧЕВЫМ СЛОВАМ:")
    print(f"{'─' * 80}\n")

    keyword_stats = {}
    for ann in announcements:
        if ann.keyword_matched not in keyword_stats:
            keyword_stats[ann.keyword_matched] = 0
        keyword_stats[ann.keyword_matched] += 1

    for keyword, count in sorted(keyword_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"   {keyword}: {count}")

    print()


def view_parsing_logs():
    """Просмотр логов парсинга"""
    from database.models import SessionLocal, ParsingLog
    from sqlalchemy import desc

    session = SessionLocal()
    try:
        logs = session.query(ParsingLog).order_by(desc(ParsingLog.started_at)).all()
    finally:
        session.close()

    print_separator("📜 ЛОГИ ПАРСИНГА")

    if not logs:
        print("⚠️  Нет логов парсинга\n")
        return

    print(f"Всего запусков парсинга: {len(logs)}\n")

    for i, log in enumerate(logs[-10:], 1):  # Последние 10
        status_emoji = {
            'running': '🔄',
            'completed': '✅',
            'failed': '❌'
        }

        print(f"{'─' * 80}")
        print(f"#{i}. {status_emoji.get(log.status, '❓')} {log.status.upper()}")
        print(f"{'─' * 80}")
        print(f"🕐 Начало: {log.started_at.strftime('%d.%m.%Y %H:%M:%S')}")

        if log.finished_at:
            duration = (log.finished_at - log.started_at).total_seconds()
            print(f"⏱️  Длительность: {duration:.1f} сек")
            print(f"📊 Найдено: {log.total_found}")
            print(f"✅ Добавлено новых: {log.new_added}")
            print(f"⏭️  Дубликатов пропущено: {log.duplicates}")

        if log.error_message:
            print(f"❌ Ошибка: {log.error_message}")

        print()


def main():
    """Главное меню"""
    print("=" * 80)
    print("🗄️  ПРОСМОТР БАЗЫ ДАННЫХ GOSZAKUP BOT".center(80))
    print("=" * 80)

    # Инициализация БД
    init_database()

    while True:
        print("\n📋 МЕНЮ:")
        print("  1. Показать все объявления")
        print("  2. Показать статистику")
        print("  3. Показать логи парсинга")
        print("  4. Показать всё")
        print("  0. Выход")

        choice = input("\nВыберите опцию (0-4): ").strip()

        if choice == '1':
            view_announcements()
        elif choice == '2':
            view_stats()
        elif choice == '3':
            view_parsing_logs()
        elif choice == '4':
            view_announcements()
            view_stats()
            view_parsing_logs()
        elif choice == '0':
            print("\n👋 До свидания!\n")
            break
        else:
            print("\n⚠️  Неверный выбор. Попробуйте снова.")


if __name__ == '__main__':
    main()

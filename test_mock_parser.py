"""
Скрипт для тестирования мокового парсера
Проверяет генерацию данных и распределение по менеджерам
"""
from parsers.mock_parser import MockGoszakupParser
from parsers.matcher import ManagerMatcher
from config import ALL_KEYWORDS


def main():
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ МОКОВОГО ПАРСЕРА")
    print("=" * 60)

    # Создаем парсер и матчер
    parser = MockGoszakupParser()
    matcher = ManagerMatcher()

    # Парсим лоты
    print(f"\n🔍 Ключевые слова для поиска: {', '.join(ALL_KEYWORDS)}")
    print()

    lots = parser.search_lots(ALL_KEYWORDS, days_back=7)

    print("\n" + "=" * 60)
    print("📋 РЕЗУЛЬТАТЫ ПАРСИНГА")
    print("=" * 60)

    for i, lot in enumerate(lots, 1):
        print(f"\n{'━' * 60}")
        print(f"ЛОТ #{i}")
        print(f"{'━' * 60}")
        print(f"📌 Номер объявления: {lot['announcement_number']}")
        print(f"📝 Название: {lot['lot_name']}")
        print(f"📄 Описание: {lot['lot_description'][:80]}...")
        print(f"🏢 Организация: {lot['organization_name']}")
        print(f"🔢 БИН: {lot['organization_bin']}")
        print(f"📍 Адрес: {lot['legal_address']}")
        print(f"🌍 Регион: {lot['region']}")
        print(f"🔑 Ключевое слово: {lot['keyword_matched']}")
        print(f"🔗 URL: {lot['announcement_url']}")

        # Проверяем распределение менеджеру
        manager = matcher.find_manager(lot)
        if manager:
            print(f"\n👤 НАЗНАЧЕН МЕНЕДЖЕР:")
            print(f"   ID: {manager['manager_id']}")
            print(f"   Имя: {manager['manager_name']}")
            print(f"   Telegram ID: {manager['telegram_id']}")
        else:
            print(f"\n⚠️  МЕНЕДЖЕР НЕ НАЙДЕН (регион не совпадает)")

    print("\n" + "=" * 60)
    print(f"✅ Всего сгенерировано лотов: {len(lots)}")
    print("=" * 60)

    # Статистика по менеджерам
    print("\n📊 СТАТИСТИКА ПО МЕНЕДЖЕРАМ:")
    print("=" * 60)

    manager_stats = {}
    unassigned = 0

    for lot in lots:
        manager = matcher.find_manager(lot)
        if manager:
            manager_id = manager['manager_id']
            if manager_id not in manager_stats:
                manager_stats[manager_id] = {
                    'name': manager['manager_name'],
                    'count': 0,
                    'regions': set()
                }
            manager_stats[manager_id]['count'] += 1
            manager_stats[manager_id]['regions'].add(lot['region'])
        else:
            unassigned += 1

    for manager_id, stats in manager_stats.items():
        print(f"\n👤 {stats['name']} (ID: {manager_id}):")
        print(f"   Лотов: {stats['count']}")
        print(f"   Регионы: {', '.join(stats['regions'])}")

    if unassigned > 0:
        print(f"\n⚠️  Не распределено: {unassigned}")

    print("\n" + "=" * 60)
    print("✅ Тестирование завершено!")
    print("=" * 60)


if __name__ == '__main__':
    main()

"""
Скрипт для тестирования парсера и системы распределения
"""
import asyncio
from parsers.goszakup import GoszakupParser
from parsers.matcher import ManagerMatcher
from config import ALL_KEYWORDS

async def test_parser():
    """Тестирование парсера"""
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ ПАРСЕРА GOSZAKUP")
    print("=" * 60)

    parser = GoszakupParser()
    matcher = ManagerMatcher()

    # Тест 1: Поиск лотов
    print("\n📋 Тест 1: Поиск лотов по ключевым словам")
    print(f"Ключевые слова: {', '.join(ALL_KEYWORDS)}")

    results = parser.search_lots(ALL_KEYWORDS, days_back=30)

    print(f"\n✅ Найдено лотов: {len(results)}")

    if results:
        print("\n" + "=" * 60)
        print("📄 ПРИМЕРЫ НАЙДЕННЫХ ЛОТОВ")
        print("=" * 60)

        for i, lot in enumerate(results[:3], 1):  # Показываем первые 3
            print(f"\n🔹 Лот {i}:")
            print(f"  Номер объявления: {lot['announcement_number']}")
            print(f"  Организация: {lot['organization_name']}")
            print(f"  Юр. адрес: {lot['legal_address']}")
            print(f"  Регион: {lot['region']}")
            print(f"  Лот: {lot['lot_name'][:80]}...")
            print(f"  Ключевое слово: {lot['keyword_matched']}")
            print(f"  URL: {lot['announcement_url']}")

            # Тест 2: Распределение по менеджерам
            manager = matcher.find_manager(lot)
            if manager:
                print(f"  👤 Менеджер: {manager['manager_name']} (ID: {manager['manager_id']})")
            else:
                print(f"  ⚠️ Менеджер не найден")

    else:
        print("\n⚠️ Лоты не найдены. Попробуйте:")
        print("  1. Увеличить days_back")
        print("  2. Проверить доступность API")
        print("  3. Изменить ключевые слова")

    # Тест 3: Статистика менеджеров
    print("\n" + "=" * 60)
    print("👥 ИНФОРМАЦИЯ О МЕНЕДЖЕРАХ")
    print("=" * 60)

    for manager_info in matcher.get_all_managers_info():
        print(f"\n{manager_info['name']} (ID: {manager_info['id']})")
        print(f"  Telegram ID: {manager_info['telegram_id']}")
        print(f"  Регионов: {manager_info['regions_count']}")
        print(f"  Ключевых слов: {manager_info['keywords_count']}")
        print(f"  Регионы: {', '.join(manager_info['regions'][:3])}...")
        print(f"  Ключевые слова: {', '.join(manager_info['keywords'])}")

    print("\n" + "=" * 60)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(test_parser())

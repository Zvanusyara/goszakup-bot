"""
Модуль для сопоставления объявлений с менеджерами
на основе регионов и ключевых слов
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MANAGERS
from typing import Optional, Dict, List


class ManagerMatcher:
    """Класс для распределения объявлений по менеджерам"""

    def __init__(self):
        self.managers = MANAGERS

    def find_managers(self, announcement: Dict) -> List[Dict]:
        """
        Найти всех подходящих менеджеров для объявления

        Args:
            announcement: Словарь с данными объявления (region, keyword_matched)

        Returns:
            Список словарей с данными менеджеров
        """
        region = announcement.get('region', '').lower()
        keyword = announcement.get('keyword_matched', '').lower()

        print(f"🔍 Поиск менеджеров для региона: {region}, ключевое слово: {keyword}")

        matched_managers = []

        # Проходим по всем менеджерам
        for manager_id, manager_data in self.managers.items():
            # Проверяем совпадение ключевого слова
            keyword_match = any(
                kw.lower() == keyword.lower()
                for kw in manager_data['keywords']
            )

            if not keyword_match:
                continue

            # Проверяем регион
            region_match = self._check_region_match(region, manager_data['regions'])

            if region_match:
                print(f"✅ Найден менеджер: {manager_data['name']} (ID: {manager_id})")
                matched_managers.append({
                    'manager_id': manager_id,
                    'manager_name': manager_data['name'],
                    'telegram_id': manager_data['telegram_id']
                })

        if not matched_managers:
            print(f"⚠️ Менеджеры не найдены для региона: {region}")
        elif len(matched_managers) > 1:
            print(f"📋 Найдено менеджеров: {len(matched_managers)} (общий регион)")

        return matched_managers

    def find_manager(self, announcement: Dict) -> Optional[Dict]:
        """
        Найти подходящего менеджера для объявления (первого из списка)

        Args:
            announcement: Словарь с данными объявления (region, keyword_matched)

        Returns:
            Словарь с данными менеджера или None
        """
        managers = self.find_managers(announcement)
        return managers[0] if managers else None

    def _check_region_match(self, announcement_region: str, manager_regions: list) -> bool:
        """
        Проверить совпадение региона объявления с регионами менеджера

        Args:
            announcement_region: Регион из объявления
            manager_regions: Список регионов менеджера

        Returns:
            True если регион совпадает
        """
        announcement_region_lower = announcement_region.lower()

        for manager_region in manager_regions:
            manager_region_lower = manager_region.lower()

            # Проверка на полное совпадение
            if announcement_region_lower == manager_region_lower:
                return True

            # Проверка на вхождение (например, "Алматы" входит в "г. Алматы")
            if announcement_region_lower in manager_region_lower or \
               manager_region_lower in announcement_region_lower:
                return True

        return False

    def get_manager_stats(self, manager_id: int) -> Dict:
        """
        Получить статистику менеджера

        Args:
            manager_id: ID менеджера

        Returns:
            Словарь со статистикой
        """
        if manager_id not in self.managers:
            return {}

        manager_data = self.managers[manager_id]

        return {
            'name': manager_data['name'],
            'telegram_id': manager_data['telegram_id'],
            'regions_count': len(manager_data['regions']),
            'keywords_count': len(manager_data['keywords']),
            'regions': manager_data['regions'],
            'keywords': manager_data['keywords']
        }

    def get_all_managers_info(self) -> list:
        """Получить информацию обо всех менеджерах"""
        return [
            {
                'id': manager_id,
                **self.get_manager_stats(manager_id)
            }
            for manager_id in self.managers.keys()
        ]


# Тестирование
if __name__ == '__main__':
    matcher = ManagerMatcher()

    # Тестовые объявления
    test_announcements = [
        {
            'region': 'г. Алматы',
            'keyword_matched': 'медицинские изделия'
        },
        {
            'region': 'Акмолинская область',
            'keyword_matched': 'аренда'
        },
        {
            'region': 'г. Астана',
            'keyword_matched': 'реагенты'
        },
        {
            'region': 'Туркестанская область',
            'keyword_matched': 'детали'
        }
    ]

    print("🧪 Тестирование распределения менеджеров:\n")

    for announcement in test_announcements:
        manager = matcher.find_manager(announcement)
        if manager:
            print(f"  Регион: {announcement['region']}")
            print(f"  Ключевое слово: {announcement['keyword_matched']}")
            print(f"  → Менеджер: {manager['manager_name']}")
            print(f"  → Telegram ID: {manager['telegram_id']}\n")
        else:
            print(f"  ❌ Менеджер не найден для {announcement['region']}\n")

    # Статистика менеджеров
    print("\n📊 Информация о менеджерах:")
    for manager_info in matcher.get_all_managers_info():
        print(f"\n  {manager_info['name']} (ID: {manager_info['id']})")
        print(f"    Telegram ID: {manager_info['telegram_id']}")
        print(f"    Регионов: {manager_info['regions_count']}")
        print(f"    Ключевых слов: {manager_info['keywords_count']}")

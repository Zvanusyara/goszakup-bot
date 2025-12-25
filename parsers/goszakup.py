"""
Парсер для API портала goszakup.gov.kz
Использует GraphQL API для поиска лотов и объявлений
"""
import requests
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GOSZAKUP_API_URL, GOSZAKUP_API_TOKEN, ALL_KEYWORDS, RESULTS_PER_PAGE


class GoszakupParser:
    """Парсер для портала госзакупок Казахстана"""

    def __init__(self):
        self.graphql_url = GOSZAKUP_API_URL
        self.rest_api_base = "https://ows.goszakup.gov.kz/v3"
        self.session = requests.Session()

        # Базовые заголовки
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        # Добавляем токен авторизации, если он есть
        if GOSZAKUP_API_TOKEN:
            headers['Authorization'] = f'Bearer {GOSZAKUP_API_TOKEN}'

        self.session.headers.update(headers)

    def search_lots(self, keywords: List[str], days_back: int = 7) -> List[Dict]:
        """
        Поиск лотов по ключевым словам за последние N дней

        Args:
            keywords: Список ключевых слов для поиска
            days_back: Количество дней назад для поиска

        Returns:
            Список найденных лотов с данными
        """
        print(f"🔍 Поиск лотов по ключевым словам: {', '.join(keywords)}")

        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        found_lots = []

        # Используем REST API v3 для поиска лотов
        # Endpoint: /lots
        lots_url = f"{self.rest_api_base}/lots"

        params = {
            'limit': RESULTS_PER_PAGE,
            'offset': 0
        }

        try:
            response = self.session.get(lots_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'items' in data:
                for lot in data['items']:
                    # Проверяем наличие ключевых слов в названии лота
                    lot_name = lot.get('name_ru', '').lower()
                    lot_desc = lot.get('description_ru', '').lower()

                    matched_keyword = None
                    for keyword in keywords:
                        if keyword.lower() in lot_name or keyword.lower() in lot_desc:
                            matched_keyword = keyword
                            break

                    if matched_keyword:
                        # Извлекаем данные лота
                        lot_data = self._extract_lot_data(lot, matched_keyword)
                        if lot_data:
                            found_lots.append(lot_data)
                            print(f"✅ Найден лот: {lot_data['lot_name'][:50]}...")

            print(f"📊 Всего найдено лотов: {len(found_lots)}")
            return found_lots

        except requests.RequestException as e:
            print(f"❌ Ошибка при поиске лотов: {e}")
            return []

    def _extract_lot_data(self, lot: Dict, keyword: str) -> Optional[Dict]:
        """Извлечь данные из лота"""
        try:
            # Получаем номер объявления
            trd_buy_id = lot.get('trd_buy_id')
            if not trd_buy_id:
                return None

            # Получаем детали объявления
            announcement_data = self.get_announcement_details(trd_buy_id)
            if not announcement_data:
                return None

            # Формируем полные данные
            return {
                'announcement_number': announcement_data.get('number_anno', 'N/A'),
                'announcement_url': f"https://goszakup.gov.kz/ru/announce/index/{trd_buy_id}",
                'organization_name': announcement_data.get('customer_name', 'N/A'),
                'organization_bin': announcement_data.get('customer_bin', 'N/A'),
                'legal_address': announcement_data.get('customer_address', 'N/A'),
                'region': self._extract_region(announcement_data.get('customer_address', '')),
                'lot_name': lot.get('name_ru', 'N/A'),
                'lot_description': lot.get('description_ru', ''),
                'keyword_matched': keyword
            }

        except Exception as e:
            print(f"⚠️ Ошибка при извлечении данных лота: {e}")
            return None

    def get_announcement_details(self, trd_buy_id: int) -> Optional[Dict]:
        """
        Получить детали объявления по ID

        Args:
            trd_buy_id: ID объявления

        Returns:
            Словарь с данными объявления
        """
        url = f"{self.rest_api_base}/trd-buy/{trd_buy_id}"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            return {
                'number_anno': data.get('number_anno', 'N/A'),
                'customer_name': data.get('name_ru', 'N/A'),
                'customer_bin': data.get('customer', {}).get('bin', 'N/A'),
                'customer_address': data.get('customer', {}).get('legal_address', 'N/A'),
                'customer_region': data.get('customer', {}).get('region', {}).get('name_ru', 'N/A')
            }

        except requests.RequestException as e:
            print(f"⚠️ Ошибка при получении деталей объявления {trd_buy_id}: {e}")
            # Пробуем альтернативный способ через GraphQL
            return self._get_announcement_graphql(trd_buy_id)

    def _get_announcement_graphql(self, trd_buy_id: int) -> Optional[Dict]:
        """Получить данные объявления через GraphQL"""
        query = """
        query($id: Int!) {
            trd_buy(id: $id) {
                id
                number_anno
                name_ru
                customer {
                    bin
                    name_ru
                    legal_address
                    region {
                        name_ru
                    }
                }
            }
        }
        """

        variables = {"id": trd_buy_id}

        try:
            response = self.session.post(
                self.graphql_url,
                json={'query': query, 'variables': variables},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if 'data' in data and data['data'].get('trd_buy'):
                buy_data = data['data']['trd_buy']
                customer = buy_data.get('customer', {})

                return {
                    'number_anno': buy_data.get('number_anno', 'N/A'),
                    'customer_name': customer.get('name_ru', 'N/A'),
                    'customer_bin': customer.get('bin', 'N/A'),
                    'customer_address': customer.get('legal_address', 'N/A'),
                    'customer_region': customer.get('region', {}).get('name_ru', 'N/A')
                }

        except Exception as e:
            print(f"⚠️ Ошибка GraphQL запроса: {e}")
            return None

    def _extract_region(self, address: str) -> str:
        """
        Извлечь регион из юридического адреса

        Args:
            address: Юридический адрес

        Returns:
            Название региона
        """
        if not address:
            return "Не указан"

        address_lower = address.lower()

        # Список областей Казахстана
        regions_map = {
            'алматинская': 'Алматинская область',
            'алматы': 'г. Алматы',
            'астана': 'г. Астана',
            'нур-султан': 'г. Астана',
            'акмолинская': 'Акмолинская область',
            'туркестанская': 'Туркестанская область',
            'шымкент': 'г. Шымкент',
            'актюбинская': 'Актюбинская область',
            'атырауская': 'Атырауская область',
            'восточно-казахстанская': 'Восточно-Казахстанская область',
            'жамбылская': 'Жамбылская область',
            'западно-казахстанская': 'Западно-Казахстанская область',
            'карагандинская': 'Карагандинская область',
            'костанайская': 'Костанайская область',
            'кызылординская': 'Кызылординская область',
            'мангистауская': 'Мангистауская область',
            'павлодарская': 'Павлодарская область',
            'северо-казахстанская': 'Северо-Казахстанская область',
            'абайская': 'Абайская область',
            'жетісуская': 'Жетісуская область',
            'улытауская': 'Улытауская область'
        }

        for key, region in regions_map.items():
            if key in address_lower:
                return region

        return "Другой регион"


# Тестирование парсера
if __name__ == '__main__':
    parser = GoszakupParser()

    # Тестовый поиск
    test_keywords = ["медицинские изделия", "аренда"]
    results = parser.search_lots(test_keywords, days_back=30)

    print(f"\n📋 Результаты тестирования:")
    print(f"Найдено лотов: {len(results)}")

    if results:
        print("\nПример первого результата:")
        first = results[0]
        for key, value in first.items():
            print(f"  {key}: {value}")

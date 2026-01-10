"""
Модуль для работы с Google Sheets API
Обеспечивает синхронизацию данных из базы данных с Google таблицей
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import gspread
from google.oauth2.service_account import Credentials
from loguru import logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    GOOGLE_SHEETS_ENABLED,
    GOOGLE_SERVICE_ACCOUNT_FILE,
    GOOGLE_SPREADSHEET_ID,
    GOOGLE_SHEET_NAME
)


class GoogleSheetsManager:
    """Менеджер для работы с Google Sheets"""

    # Области доступа для Google Sheets API
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    # Заголовки столбцов в Google Sheets
    HEADERS = [
        'Дата добавления',
        'Дата окончания приема заявок',
        'Номер объявления',
        'Ссылка',
        'Организация',
        'Регион',
        'Лоты',
        'Ключевые слова',
        'Менеджер',
        'Статус',
        'Причина отказа',
        'Детали участия',
        'Дата ответа'
    ]

    def __init__(self):
        """Инициализация менеджера Google Sheets"""
        self.enabled = GOOGLE_SHEETS_ENABLED
        self.client = None
        self.spreadsheet = None
        self.worksheet = None

        if self.enabled:
            self._initialize()

    def _initialize(self):
        """Инициализация подключения к Google Sheets"""
        try:
            # Проверка наличия файла учетных данных
            if not os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
                logger.warning(
                    f"Файл учетных данных Google не найден: {GOOGLE_SERVICE_ACCOUNT_FILE}"
                )
                self.enabled = False
                return

            # Авторизация
            credentials = Credentials.from_service_account_file(
                GOOGLE_SERVICE_ACCOUNT_FILE,
                scopes=self.SCOPES
            )
            self.client = gspread.authorize(credentials)

            # Открытие таблицы
            self.spreadsheet = self.client.open_by_key(GOOGLE_SPREADSHEET_ID)

            # Получение или создание листа
            try:
                self.worksheet = self.spreadsheet.worksheet(GOOGLE_SHEET_NAME)
            except gspread.WorksheetNotFound:
                logger.info(f"Создание нового листа: {GOOGLE_SHEET_NAME}")
                self.worksheet = self.spreadsheet.add_worksheet(
                    title=GOOGLE_SHEET_NAME,
                    rows=1000,
                    cols=len(self.HEADERS)
                )

            # Инициализация заголовков
            self._initialize_headers()

            logger.success("Google Sheets успешно инициализирован")

        except Exception as e:
            logger.error(f"Ошибка инициализации Google Sheets: {e}")
            self.enabled = False

    def _initialize_headers(self):
        """Инициализация заголовков таблицы"""
        try:
            # Проверка, есть ли уже заголовки
            existing_headers = self.worksheet.row_values(1)

            if not existing_headers or existing_headers != self.HEADERS:
                # Очистка всей первой строки (удаление старых заголовков)
                self.worksheet.batch_clear(['1:1'])

                # Установка новых заголовков
                self.worksheet.update('A1', [self.HEADERS])

                # Форматирование заголовков (жирный шрифт, фон)
                # Диапазон зависит от количества столбцов
                header_range = f'A1:{chr(64 + len(self.HEADERS))}1'
                self.worksheet.format(header_range, {
                    'backgroundColor': {
                        'red': 0.27,
                        'green': 0.45,
                        'blue': 0.77
                    },
                    'textFormat': {
                        'foregroundColor': {
                            'red': 1.0,
                            'green': 1.0,
                            'blue': 1.0
                        },
                        'fontSize': 10,
                        'bold': True
                    },
                    'horizontalAlignment': 'CENTER',
                    'verticalAlignment': 'MIDDLE'
                })

                # Заморозить первую строку
                self.worksheet.freeze(rows=1)

                # Удалить лишние столбцы если их больше чем нужно
                current_col_count = self.worksheet.col_count
                needed_col_count = len(self.HEADERS)
                if current_col_count > needed_col_count:
                    # Удаляем столбцы справа от нужного количества
                    self.worksheet.delete_columns(needed_col_count + 1, current_col_count)
                    logger.info(f"Удалено {current_col_count - needed_col_count} лишних столбцов")

                logger.info("Заголовки инициализированы")

        except Exception as e:
            logger.error(f"Ошибка инициализации заголовков: {e}")

    def _utc_to_local(self, utc_dt: datetime) -> datetime:
        """
        Конвертация UTC времени в местное время Казахстана (UTC+5)

        Args:
            utc_dt: Время в UTC

        Returns:
            Время в часовом поясе Казахстана
        """
        if utc_dt:
            return utc_dt + timedelta(hours=5)
        return None

    def _announcement_to_row(self, announcement) -> List[Any]:
        """
        Преобразование объявления в строку для Google Sheets

        Args:
            announcement: Объект Announcement из БД

        Returns:
            Список значений для строки
        """
        import json

        # Конвертируем UTC время в местное время Казахстана
        created_at_local = self._utc_to_local(announcement.created_at)
        response_at_local = self._utc_to_local(announcement.response_at)

        # ВАЖНО: application_deadline уже приходит в местном времени Казахстана из API
        # поэтому НЕ применяем _utc_to_local()
        application_deadline_str = ''
        if announcement.application_deadline:
            application_deadline_str = announcement.application_deadline.strftime('%Y-%m-%d %H:%M:%S')

        # Форматируем лоты для Google Sheets (через перенос строки)
        lots_str = ''
        keywords_str = announcement.keyword_matched or ''

        if announcement.lots:
            try:
                # Десериализуем JSON
                lots_data = json.loads(announcement.lots) if isinstance(announcement.lots, str) else announcement.lots

                if lots_data and isinstance(lots_data, list):
                    # Форматируем каждый лот
                    lot_lines = []
                    for i, lot in enumerate(lots_data, 1):
                        lot_number = lot.get('number')  # Реальный номер лота
                        lot_name = lot.get('name', 'N/A')

                        # Используем реальный номер лота если есть, иначе порядковый
                        lot_display = f"№{lot_number}" if lot_number else f"{i}"
                        lot_lines.append(f"ЛОТ {lot_display}: {lot_name}")

                    # Объединяем через перенос строки
                    lots_str = '\n'.join(lot_lines)
            except:
                # Фолбэк на старый формат
                lots_str = announcement.lot_name or ''
        else:
            # Старый формат - один лот
            lots_str = announcement.lot_name or ''

        return [
            created_at_local.strftime('%Y-%m-%d %H:%M:%S') if created_at_local else '',
            application_deadline_str,
            announcement.announcement_number or '',
            announcement.announcement_url or '',
            announcement.organization_name or '',
            announcement.region or '',
            lots_str,
            keywords_str,
            announcement.manager_name or '',
            self._format_status(announcement.status),
            announcement.rejection_reason or '',
            announcement.participation_details or '',
            response_at_local.strftime('%Y-%m-%d %H:%M:%S') if response_at_local else ''
        ]

    def _format_status(self, status: str) -> str:
        """Форматирование статуса для отображения"""
        status_map = {
            'pending': 'Ожидает',
            'accepted': 'Принято',
            'rejected': 'Отклонено'
        }
        return status_map.get(status, status)

    def _find_row_by_number(self, announcement_number: str) -> Optional[int]:
        """
        Найти номер строки по номеру объявления

        Args:
            announcement_number: Номер объявления

        Returns:
            Номер строки или None
        """
        try:
            # Получить все значения из столбца C (Номер объявления)
            number_column = self.worksheet.col_values(3)

            # Найти строку с нужным номером объявления
            for idx, cell_value in enumerate(number_column[1:], start=2):  # Пропускаем заголовок
                if cell_value and cell_value == announcement_number:
                    return idx

            return None

        except Exception as e:
            logger.error(f"Ошибка поиска строки по номеру {announcement_number}: {e}")
            return None

    def add_announcement(self, announcement) -> bool:
        """
        Добавить новое объявление в Google Sheets

        Args:
            announcement: Объект Announcement из БД

        Returns:
            True если успешно, False при ошибке
        """
        if not self.enabled:
            return False

        try:
            # Проверка, не добавлено ли уже это объявление
            existing_row = self._find_row_by_number(announcement.announcement_number)
            if existing_row:
                logger.warning(f"Объявление {announcement.announcement_number} уже существует в строке {existing_row}")
                return self.update_announcement(announcement)

            # Преобразование объявления в строку
            row_data = self._announcement_to_row(announcement)

            # Добавление строки
            self.worksheet.append_row(row_data, value_input_option='USER_ENTERED')

            # Применение цветового кодирования статуса
            row_number = len(self.worksheet.col_values(1))
            self._apply_status_formatting(row_number, announcement.status)

            logger.info(f"Объявление {announcement.announcement_number} добавлено в Google Sheets")
            return True

        except Exception as e:
            logger.error(f"Ошибка добавления объявления {announcement.announcement_number} в Google Sheets: {e}")
            return False

    def update_announcement(self, announcement) -> bool:
        """
        Обновить существующее объявление в Google Sheets

        Args:
            announcement: Объект Announcement из БД

        Returns:
            True если успешно, False при ошибке
        """
        if not self.enabled:
            return False

        try:
            # Найти строку с этим объявлением
            row_number = self._find_row_by_number(announcement.announcement_number)

            if not row_number:
                logger.warning(f"Объявление {announcement.announcement_number} не найдено в Google Sheets, добавляем")
                return self.add_announcement(announcement)

            # Преобразование объявления в строку
            row_data = self._announcement_to_row(announcement)

            # Обновление строки (столбцы A-M: 13 столбцов)
            range_name = f'A{row_number}:M{row_number}'
            self.worksheet.update(range_name, [row_data], value_input_option='USER_ENTERED')

            # Применение цветового кодирования статуса
            self._apply_status_formatting(row_number, announcement.status)

            logger.info(f"Объявление {announcement.announcement_number} обновлено в Google Sheets (строка {row_number})")
            return True

        except Exception as e:
            logger.error(f"Ошибка обновления объявления {announcement.announcement_number} в Google Sheets: {e}")
            return False

    def _apply_status_formatting(self, row_number: int, status: str):
        """
        Применить цветовое форматирование в зависимости от статуса

        Args:
            row_number: Номер строки
            status: Статус объявления
        """
        try:
            # Определение цвета в зависимости от статуса
            if status == 'accepted':
                # Зеленый для принятых
                color = {
                    'red': 0.78,
                    'green': 0.94,
                    'blue': 0.81
                }
            elif status == 'rejected':
                # Красный для отклоненных
                color = {
                    'red': 1.0,
                    'green': 0.78,
                    'blue': 0.81
                }
            else:
                # Желтый для ожидающих
                color = {
                    'red': 1.0,
                    'green': 0.92,
                    'blue': 0.61
                }

            # Найти позицию столбца "Статус" в заголовках
            status_column_index = self.HEADERS.index('Статус') + 1  # +1 так как индексация с 1
            status_column_letter = chr(64 + status_column_index)  # A=65, поэтому 64+1=A

            # Применение цвета к столбцу статуса
            range_name = f'{status_column_letter}{row_number}'
            self.worksheet.format(range_name, {
                'backgroundColor': color
            })

        except Exception as e:
            logger.error(f"Ошибка применения форматирования к строке {row_number}: {e}")

    def sync_all_announcements(self, announcements: List) -> Dict[str, int]:
        """
        Синхронизация всех объявлений из БД с Google Sheets

        Args:
            announcements: Список объектов Announcement

        Returns:
            Словарь со статистикой: {'added': N, 'updated': N, 'errors': N}
        """
        if not self.enabled:
            return {'added': 0, 'updated': 0, 'errors': 0}

        stats = {'added': 0, 'updated': 0, 'errors': 0}

        try:
            # Получить все существующие номера объявлений
            existing_numbers = set()
            number_column = self.worksheet.col_values(3)  # Столбец C - Номер объявления

            for cell_value in number_column[1:]:  # Пропускаем заголовок
                if cell_value:
                    existing_numbers.add(cell_value)

            # Обработка каждого объявления
            for announcement in announcements:
                try:
                    if announcement.announcement_number in existing_numbers:
                        if self.update_announcement(announcement):
                            stats['updated'] += 1
                        else:
                            stats['errors'] += 1
                    else:
                        if self.add_announcement(announcement):
                            stats['added'] += 1
                        else:
                            stats['errors'] += 1
                except Exception as e:
                    logger.error(f"Ошибка синхронизации объявления {announcement.announcement_number}: {e}")
                    stats['errors'] += 1

            logger.success(
                f"Синхронизация завершена: "
                f"добавлено {stats['added']}, "
                f"обновлено {stats['updated']}, "
                f"ошибок {stats['errors']}"
            )

            return stats

        except Exception as e:
            logger.error(f"Ошибка синхронизации всех объявлений: {e}")
            return stats


# Глобальный экземпляр менеджера
_sheets_manager = None


def get_sheets_manager() -> GoogleSheetsManager:
    """Получить глобальный экземпляр менеджера Google Sheets"""
    global _sheets_manager

    if _sheets_manager is None:
        _sheets_manager = GoogleSheetsManager()

    return _sheets_manager

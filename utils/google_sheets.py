"""
Модуль для работы с Google Sheets API
Обеспечивает синхронизацию данных из базы данных с Google таблицей
"""
import os
import sys
from datetime import datetime
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
        'ID',
        'Дата создания',
        'Номер объявления',
        'Ссылка',
        'Организация',
        'БИН',
        'Юридический адрес',
        'Регион',
        'Название лота',
        'Описание лота',
        'Ключевое слово',
        'ID менеджера',
        'Менеджер',
        'Статус',
        'Причина отказа',
        'Дата обновления',
        'Дата ответа',
        'Уведомление отправлено',
        'Админ уведомлен'
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
                # Установка заголовков
                self.worksheet.update('A1', [self.HEADERS])

                # Форматирование заголовков (жирный шрифт, фон)
                self.worksheet.format('A1:S1', {
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

                logger.info("Заголовки инициализированы")

        except Exception as e:
            logger.error(f"Ошибка инициализации заголовков: {e}")

    def _announcement_to_row(self, announcement) -> List[Any]:
        """
        Преобразование объявления в строку для Google Sheets

        Args:
            announcement: Объект Announcement из БД

        Returns:
            Список значений для строки
        """
        return [
            announcement.id,
            announcement.created_at.strftime('%Y-%m-%d %H:%M:%S') if announcement.created_at else '',
            announcement.announcement_number or '',
            announcement.announcement_url or '',
            announcement.organization_name or '',
            announcement.organization_bin or '',
            announcement.legal_address or '',
            announcement.region or '',
            announcement.lot_name or '',
            announcement.lot_description or '',
            announcement.keyword_matched or '',
            announcement.manager_id or '',
            announcement.manager_name or '',
            self._format_status(announcement.status),
            announcement.rejection_reason or '',
            announcement.updated_at.strftime('%Y-%m-%d %H:%M:%S') if announcement.updated_at else '',
            announcement.response_at.strftime('%Y-%m-%d %H:%M:%S') if announcement.response_at else '',
            'Да' if announcement.notification_sent else 'Нет',
            'Да' if announcement.admin_notified else 'Нет'
        ]

    def _format_status(self, status: str) -> str:
        """Форматирование статуса для отображения"""
        status_map = {
            'pending': 'Ожидает',
            'accepted': 'Принято',
            'rejected': 'Отклонено'
        }
        return status_map.get(status, status)

    def _find_row_by_id(self, announcement_id: int) -> Optional[int]:
        """
        Найти номер строки по ID объявления

        Args:
            announcement_id: ID объявления

        Returns:
            Номер строки или None
        """
        try:
            # Получить все значения из столбца A (ID)
            id_column = self.worksheet.col_values(1)

            # Найти строку с нужным ID
            for idx, cell_value in enumerate(id_column[1:], start=2):  # Пропускаем заголовок
                if cell_value and int(cell_value) == announcement_id:
                    return idx

            return None

        except Exception as e:
            logger.error(f"Ошибка поиска строки по ID {announcement_id}: {e}")
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
            existing_row = self._find_row_by_id(announcement.id)
            if existing_row:
                logger.warning(f"Объявление {announcement.id} уже существует в строке {existing_row}")
                return self.update_announcement(announcement)

            # Преобразование объявления в строку
            row_data = self._announcement_to_row(announcement)

            # Добавление строки
            self.worksheet.append_row(row_data, value_input_option='USER_ENTERED')

            # Применение цветового кодирования статуса
            row_number = len(self.worksheet.col_values(1))
            self._apply_status_formatting(row_number, announcement.status)

            logger.info(f"Объявление {announcement.id} добавлено в Google Sheets")
            return True

        except Exception as e:
            logger.error(f"Ошибка добавления объявления {announcement.id} в Google Sheets: {e}")
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
            row_number = self._find_row_by_id(announcement.id)

            if not row_number:
                logger.warning(f"Объявление {announcement.id} не найдено в Google Sheets, добавляем")
                return self.add_announcement(announcement)

            # Преобразование объявления в строку
            row_data = self._announcement_to_row(announcement)

            # Обновление строки
            range_name = f'A{row_number}:S{row_number}'
            self.worksheet.update(range_name, [row_data], value_input_option='USER_ENTERED')

            # Применение цветового кодирования статуса
            self._apply_status_formatting(row_number, announcement.status)

            logger.info(f"Объявление {announcement.id} обновлено в Google Sheets (строка {row_number})")
            return True

        except Exception as e:
            logger.error(f"Ошибка обновления объявления {announcement.id} в Google Sheets: {e}")
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

            # Применение цвета к столбцу статуса (столбец N)
            range_name = f'N{row_number}'
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
            # Получить все существующие ID
            existing_ids = set()
            id_column = self.worksheet.col_values(1)
            for cell_value in id_column[1:]:  # Пропускаем заголовок
                if cell_value:
                    try:
                        existing_ids.add(int(cell_value))
                    except ValueError:
                        pass

            # Обработка каждого объявления
            for announcement in announcements:
                try:
                    if announcement.id in existing_ids:
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
                    logger.error(f"Ошибка синхронизации объявления {announcement.id}: {e}")
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

"""
Скрипт для отладки подключения к Google Sheets
"""
import sys
import os
# Добавить корень проекта в sys.path для импортов
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import traceback
from config import (
    GOOGLE_SHEETS_ENABLED,
    GOOGLE_SERVICE_ACCOUNT_FILE,
    GOOGLE_SPREADSHEET_ID,
    GOOGLE_SHEET_NAME
)

print("=" * 60)
print("🔍 Отладка Google Sheets")
print("=" * 60)

# Шаг 1: Проверка настроек
print("\n📋 Шаг 1: Проверка настроек")
print(f"GOOGLE_SHEETS_ENABLED: {GOOGLE_SHEETS_ENABLED} (тип: {type(GOOGLE_SHEETS_ENABLED)})")
print(f"GOOGLE_SERVICE_ACCOUNT_FILE: {GOOGLE_SERVICE_ACCOUNT_FILE}")
print(f"GOOGLE_SPREADSHEET_ID: {GOOGLE_SPREADSHEET_ID}")
print(f"GOOGLE_SHEET_NAME: {GOOGLE_SHEET_NAME}")

if not GOOGLE_SHEETS_ENABLED:
    print("\n❌ GOOGLE_SHEETS_ENABLED = False")
    print("Измените в .env на: GOOGLE_SHEETS_ENABLED=True")
    exit(1)

# Шаг 2: Проверка файла учетных данных
print("\n📋 Шаг 2: Проверка файла учетных данных")
if os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
    print(f"✅ Файл существует: {GOOGLE_SERVICE_ACCOUNT_FILE}")
    print(f"Размер: {os.path.getsize(GOOGLE_SERVICE_ACCOUNT_FILE)} байт")
else:
    print(f"❌ Файл НЕ найден: {GOOGLE_SERVICE_ACCOUNT_FILE}")
    exit(1)

# Шаг 3: Проверка содержимого файла
print("\n📋 Шаг 3: Проверка JSON файла")
try:
    import json
    with open(GOOGLE_SERVICE_ACCOUNT_FILE, 'r') as f:
        creds = json.load(f)
    print(f"✅ JSON корректный")
    print(f"Service account email: {creds.get('client_email', 'НЕ НАЙДЕН')}")
    print(f"Project ID: {creds.get('project_id', 'НЕ НАЙДЕН')}")
except Exception as e:
    print(f"❌ Ошибка чтения JSON: {e}")
    traceback.print_exc()
    exit(1)

# Шаг 4: Импорт библиотек
print("\n📋 Шаг 4: Проверка библиотек")
try:
    import gspread
    from google.oauth2.service_account import Credentials
    print("✅ Библиотеки импортированы")
except Exception as e:
    print(f"❌ Ошибка импорта: {e}")
    traceback.print_exc()
    exit(1)

# Шаг 5: Авторизация
print("\n📋 Шаг 5: Авторизация")
try:
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    credentials = Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    print("✅ Credentials созданы")

    client = gspread.authorize(credentials)
    print("✅ Клиент авторизован")
except Exception as e:
    print(f"❌ Ошибка авторизации: {e}")
    traceback.print_exc()
    exit(1)

# Шаг 6: Открытие таблицы
print("\n📋 Шаг 6: Открытие таблицы")
try:
    spreadsheet = client.open_by_key(GOOGLE_SPREADSHEET_ID)
    print(f"✅ Таблица открыта: {spreadsheet.title}")
    print(f"URL: {spreadsheet.url}")
except Exception as e:
    print(f"❌ Ошибка открытия таблицы: {e}")
    print("\nВозможные причины:")
    print("1. Неверный GOOGLE_SPREADSHEET_ID")
    print("2. Сервисному аккаунту не предоставлен доступ к таблице")
    print(f"   Email сервисного аккаунта: {creds.get('client_email')}")
    traceback.print_exc()
    exit(1)

# Шаг 7: Получение или создание листа
print("\n📋 Шаг 7: Получение/создание листа")
try:
    try:
        worksheet = spreadsheet.worksheet(GOOGLE_SHEET_NAME)
        print(f"✅ Лист уже существует: {worksheet.title}")
    except gspread.WorksheetNotFound:
        print(f"⚠️ Лист '{GOOGLE_SHEET_NAME}' не найден, создаю...")
        worksheet = spreadsheet.add_worksheet(
            title=GOOGLE_SHEET_NAME,
            rows=1000,
            cols=19
        )
        print(f"✅ Лист создан: {worksheet.title}")

    print(f"Строк: {worksheet.row_count}")
    print(f"Столбцов: {worksheet.col_count}")
except Exception as e:
    print(f"❌ Ошибка работы с листом: {e}")
    traceback.print_exc()
    exit(1)

# Шаг 8: Проверка/создание заголовков
print("\n📋 Шаг 8: Проверка заголовков")
try:
    HEADERS = [
        'ID', 'Дата создания', 'Номер объявления', 'Ссылка',
        'Организация', 'БИН', 'Юридический адрес', 'Регион',
        'Название лота', 'Описание лота', 'Ключевое слово',
        'ID менеджера', 'Менеджер', 'Статус', 'Причина отказа',
        'Дата обновления', 'Дата ответа', 'Уведомление отправлено',
        'Админ уведомлен'
    ]

    existing_headers = worksheet.row_values(1)

    if not existing_headers or existing_headers != HEADERS:
        print("⚠️ Заголовки не установлены или неверные, обновляю...")
        worksheet.update('A1', [HEADERS])
        print("✅ Заголовки обновлены")

        # Форматирование
        worksheet.format('A1:S1', {
            'backgroundColor': {'red': 0.27, 'green': 0.45, 'blue': 0.77},
            'textFormat': {
                'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0},
                'fontSize': 10,
                'bold': True
            },
            'horizontalAlignment': 'CENTER',
            'verticalAlignment': 'MIDDLE'
        })
        worksheet.freeze(rows=1)
        print("✅ Форматирование применено")
    else:
        print("✅ Заголовки уже установлены корректно")

except Exception as e:
    print(f"❌ Ошибка работы с заголовками: {e}")
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 60)
print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
print("=" * 60)
print(f"\nТаблица готова: {spreadsheet.url}")
print(f"Лист: {GOOGLE_SHEET_NAME}")

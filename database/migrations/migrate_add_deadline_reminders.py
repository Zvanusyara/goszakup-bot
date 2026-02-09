"""
Миграция: добавление полей для отслеживания напоминаний о дедлайнах
"""
import sqlite3
import sys
import os

# Добавить корень проекта в sys.path (2 уровня вверх)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import DATABASE_URL

# Извлечь путь к БД из DATABASE_URL
db_path = DATABASE_URL.replace('sqlite:///', '')

print(f"🔄 Миграция БД: {db_path}")

# Подключение к БД
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Проверить, существуют ли уже поля
    cursor.execute("PRAGMA table_info(announcements)")
    columns = [column[1] for column in cursor.fetchall()]

    fields_to_add = [
        ('reminder_48h_sent', 'BOOLEAN DEFAULT 0'),
        ('reminder_24h_sent', 'BOOLEAN DEFAULT 0'),
        ('reminder_2h_sent', 'BOOLEAN DEFAULT 0')
    ]

    for field_name, field_type in fields_to_add:
        if field_name not in columns:
            print(f"➕ Добавление поля: {field_name}")
            cursor.execute(f"ALTER TABLE announcements ADD COLUMN {field_name} {field_type}")
        else:
            print(f"✅ Поле {field_name} уже существует")

    conn.commit()
    print("✅ Миграция завершена успешно!")

except Exception as e:
    print(f"❌ Ошибка миграции: {e}")
    conn.rollback()

finally:
    conn.close()

"""
Миграция: добавление поля lots для хранения массива лотов в JSON
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
    # Проверить, существует ли уже поле
    cursor.execute("PRAGMA table_info(announcements)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'lots' not in columns:
        print(f"➕ Добавление поля: lots")
        cursor.execute("ALTER TABLE announcements ADD COLUMN lots TEXT")

        # Сделать старые поля nullable
        print(f"✅ Поле lots добавлено")
        print(f"⚠️ ВАЖНО: Поля lot_name и lot_description теперь nullable (устаревшие)")
    else:
        print(f"✅ Поле lots уже существует")

    conn.commit()
    print("✅ Миграция завершена успешно!")

except Exception as e:
    print(f"❌ Ошибка миграции: {e}")
    conn.rollback()

finally:
    conn.close()

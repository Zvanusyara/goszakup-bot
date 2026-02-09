"""
Миграция: Добавление поля participation_details_draft
"""
import sqlite3
import sys
import os

# Добавить корень проекта в sys.path (2 уровня вверх)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Путь к базе данных
DB_PATH = 'goszakup.db'

def migrate():
    """Добавить поле participation_details_draft в таблицу announcements"""

    if not os.path.exists(DB_PATH):
        print(f"❌ База данных не найдена: {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Проверить, существует ли уже поле
        cursor.execute("PRAGMA table_info(announcements)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'participation_details_draft' in columns:
            print("✅ Поле participation_details_draft уже существует")
            return True

        # Добавить новое поле
        cursor.execute("""
            ALTER TABLE announcements
            ADD COLUMN participation_details_draft TEXT
        """)

        conn.commit()
        print("✅ Поле participation_details_draft успешно добавлено!")
        return True

    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == '__main__':
    print("🔄 Запуск миграции...")
    success = migrate()

    if success:
        print("✅ Миграция завершена успешно!")
    else:
        print("❌ Миграция не удалась")

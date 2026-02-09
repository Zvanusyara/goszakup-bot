"""
Миграция: добавление поля expired_at и пометка истекших объявлений
"""
from datetime import datetime
import sqlite3
import sys
import os

# Добавить корень проекта в sys.path (2 уровня вверх)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import DATABASE_URL

def migrate():
    # Извлекаем путь к SQLite БД из URL
    db_path = DATABASE_URL.replace('sqlite:///', '')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("🔄 Начало миграции...")

    # 1. Добавляем колонку expired_at, если её нет
    try:
        cursor.execute("ALTER TABLE announcements ADD COLUMN expired_at DATETIME")
        print("✅ Добавлена колонка expired_at")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("⚠️  Колонка expired_at уже существует")
        else:
            raise

    # 2. Находим все объявления с истекшим дедлайном
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("""
        SELECT id, announcement_number, application_deadline, status
        FROM announcements
        WHERE application_deadline < ? AND status != 'expired'
    """, (now,))

    expired_announcements = cursor.fetchall()
    count = len(expired_announcements)

    print(f"📊 Найдено объявлений с истекшим сроком: {count}")

    # 3. Обновляем статус и устанавливаем expired_at
    if count > 0:
        cursor.execute("""
            UPDATE announcements
            SET status = 'expired', expired_at = ?
            WHERE application_deadline < ? AND status != 'expired'
        """, (now, now))

        conn.commit()
        print(f"✅ Обновлено записей: {cursor.rowcount}")

    # 4. Проверяем результат
    cursor.execute("SELECT status, COUNT(*) FROM announcements GROUP BY status")
    stats = cursor.fetchall()

    print("\n📈 Финальная статистика по статусам:")
    for status, cnt in stats:
        print(f"   {status}: {cnt}")

    conn.close()
    print("\n✅ Миграция завершена успешно!")

if __name__ == '__main__':
    migrate()

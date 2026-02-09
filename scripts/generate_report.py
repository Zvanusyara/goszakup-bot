"""
Скрипт для генерации Excel отчета
"""
import sys
import os
# Добавить корень проекта в sys.path для импортов
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from reports.excel import ExcelReportGenerator
from database.models import init_database


def main():
    """Генерация отчета"""
    print("=" * 60)
    print("📊 ГЕНЕРАЦИЯ ОТЧЕТА")
    print("=" * 60)

    # Инициализация БД
    init_database()

    generator = ExcelReportGenerator()

    # Выбор периода
    print("\nВыберите период для отчета:")
    print("1. За всё время")
    print("2. За последние 7 дней")
    print("3. За последние 30 дней")
    print("4. За сегодня")

    choice = input("\nВведите номер (1-4): ").strip()

    start_date = None
    end_date = datetime.now()

    if choice == '2':
        start_date = datetime.now() - timedelta(days=7)
    elif choice == '3':
        start_date = datetime.now() - timedelta(days=30)
    elif choice == '4':
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Фильтр по менеджеру
    manager_id = None
    manager_filter = input("\nФильтровать по менеджеру? (1/2/Enter для всех): ").strip()

    if manager_filter in ['1', '2']:
        manager_id = int(manager_filter)

    # Генерация отчета
    print("\n⏳ Генерация отчета...")

    try:
        report_path = generator.generate_report(
            start_date=start_date,
            end_date=end_date,
            manager_id=manager_id
        )

        print(f"\n✅ Отчет успешно создан!")
        print(f"📁 Путь: {report_path}")
        print(f"\n💡 Совет: Откройте файл в Excel или LibreOffice")

    except Exception as e:
        print(f"\n❌ Ошибка при создании отчета: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

"""
Скрипт для генерации и отправки еженедельного отчета админу
"""
import asyncio
import sys
import os
# Добавить корень проекта в sys.path для импортов
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta

from reports.excel import ExcelReportGenerator
from aiogram import Bot
from config import TELEGRAM_BOT_TOKEN, ADMIN_TELEGRAM_ID
from aiogram.types import FSInputFile


async def send_weekly_report():
    """Генерация и отправка еженедельного отчета"""

    # Определить текущую неделю (понедельник - воскресенье)
    today = datetime.now()

    # Найти понедельник текущей недели
    days_since_monday = today.weekday()  # 0 = понедельник, 6 = воскресенье
    monday = today - timedelta(days=days_since_monday)
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)

    # Найти воскресенье текущей недели
    sunday = monday + timedelta(days=6)
    sunday = sunday.replace(hour=23, minute=59, second=59, microsecond=999999)

    print(f"📅 Генерация отчета за неделю:")
    print(f"   С: {monday.strftime('%d.%m.%Y %H:%M')}")
    print(f"   По: {sunday.strftime('%d.%m.%Y %H:%M')}")

    # Генерация отчета
    generator = ExcelReportGenerator()
    report_path = generator.generate_report(
        start_date=monday,
        end_date=sunday
    )

    print(f"✅ Отчет создан: {report_path}")

    # Проверка наличия админа
    if not ADMIN_TELEGRAM_ID or ADMIN_TELEGRAM_ID == 'YOUR_ADMIN_ID':
        print("⚠️ ADMIN_TELEGRAM_ID не настроен")
        return

    # Отправка в Telegram
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    try:
        # Подготовка файла
        document = FSInputFile(report_path)

        # Формирование сообщения
        week_start = monday.strftime('%d.%m.%Y')
        week_end = sunday.strftime('%d.%m.%Y')

        message = (
            f"📊 <b>Еженедельный отчет</b>\n\n"
            f"📅 Период: {week_start} - {week_end}\n"
            f"📁 Отчет во вложении"
        )

        # Отправка
        await bot.send_document(
            chat_id=int(ADMIN_TELEGRAM_ID),
            document=document,
            caption=message,
            parse_mode='HTML'
        )

        print(f"✅ Отчет отправлен админу (ID: {ADMIN_TELEGRAM_ID})")

    except Exception as e:
        print(f"❌ Ошибка отправки отчета: {e}")

    finally:
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(send_weekly_report())

# Структура проекта Goszakup Bot

## Директории

### bot/
Telegram бот для взаимодействия с пользователями
- `handlers.py` - Обработчики команд и callback-кнопок (admin, manager, coordinator)
- `keyboards.py` - Inline и Reply клавиатуры
- `messages.py` - Форматирование сообщений
- `notifier.py` - Отправка уведомлений в Telegram

### database/
Слой работы с базой данных (SQLAlchemy + SQLite)
- `models.py` - ORM модели (Announcement, ManagerAction, ParsingLog, DeadlineReminder)
- `crud.py` - CRUD операции
- **migrations/** - Скрипты миграций БД
  - `migrate_add_deadline_reminders.py`
  - `migrate_add_draft_field.py`
  - `migrate_add_lots_field.py`
  - `migrate_cleanup_expired.py`

### parsers/
Парсинг портала госзакупок
- `goszakup.py` - GraphQL API парсер портала goszakup.gov.kz
- `matcher.py` - Распределение объявлений по менеджерам
- `mock_parser.py` - Мок-парсер для тестирования

### reports/
Генерация отчетов
- `excel.py` - Генератор Excel отчетов (openpyxl)

### scripts/
Утилитные скрипты для обслуживания системы
- `generate_report.py` - Генерация отчетов
- `send_weekly_report.py` - Отправка еженедельного отчета
- `sync_google_sheets.py` - Синхронизация с Google Sheets
- `view_database.py` - Просмотр содержимого БД
- `init_google_sheets.py` - Инициализация Google Sheets
- `debug_google_sheets.py` - Отладка Google Sheets
- `cleanup.sh` - Автоматическая очистка временных файлов

### tests/
Pytest тесты
- `conftest.py` - Fixtures
- `test_parser.py` - Тесты парсера
- `test_cleanup_logic.py` - Тесты очистки
- `test_database_models.py` - Тесты моделей БД
- `test_google_sheets.py` - Тесты Google Sheets
- `test_integration.py` - Интеграционные тесты

### utils/
Вспомогательные утилиты
- `logger.py` - Настройка логирования (loguru)
- `google_sheets.py` - Работа с Google Sheets API

## Основные файлы

- **main.py** - Точка входа, главный файл запуска
- **config.py** - Конфигурация (менеджеры, ключевые слова, настройки)
- **.env** - Переменные окружения (токены, API ключи) - НЕ в git
- **requirements.txt** - Зависимости Python
- **pytest.ini** - Конфигурация pytest
- **Dockerfile** - Docker конфигурация
- **docker-compose.yml** - Docker Compose конфигурация

## Документация

- **README.md** - Основная документация
- **INSTALL.md** - Инструкция по установке
- **TESTING.md** - Инструкция по тестированию
- **QUICKSTART_TEST.md** - Быстрый старт
- **GOOGLE_SHEETS_SETUP.md** - Настройка Google Sheets
- **DOCKER.md** - Документация Docker
- **STRUCTURE.md** - Этот файл (структура проекта)

## Технологии

- **Python 3.11+**
- **aiogram 3.15.0** - Telegram Bot Framework
- **SQLAlchemy 2.0** - ORM
- **APScheduler 3.10** - Планировщик задач
- **gspread 6.1** - Google Sheets API
- **loguru 0.7** - Логирование
- **pytest** - Тестирование

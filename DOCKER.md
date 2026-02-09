# Запуск бота в Docker

## Быстрый старт

### 1. Создайте файл .env

Скопируйте `.env.example` в `.env` и заполните необходимые значения:

```bash
cp .env.example .env
```

Отредактируйте `.env` и добавьте:
- `TELEGRAM_BOT_TOKEN` - токен вашего Telegram бота
- `GOSZAKUP_API_TOKEN` - токен API Goszakup
- Другие необходимые параметры

### 2. Убедитесь, что файл credentials существует

Проверьте, что файл `credentials/google_service_account.json` находится на месте (если используете Google Sheets).

### 3. Запустите бота

```bash
# Сборка и запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down

# Перезапуск
docker-compose restart
```

## Полезные команды

```bash
# Пересобрать образ (после изменения кода)
docker-compose up -d --build

# Просмотр статуса
docker-compose ps

# Просмотр логов за последние 100 строк
docker-compose logs --tail=100

# Зайти в контейнер
docker-compose exec goszakup-bot bash

# Удалить всё (контейнер + образ)
docker-compose down --rmi all

# Просмотр использования ресурсов
docker stats goszakup-bot
```

## Структура volumes

Данные сохраняются локально через Docker volumes:
- `./goszakup.db` - база данных SQLite
- `./logs` - логи приложения
- `./credentials` - credentials для Google Sheets (read-only)

## Обновление кода

После изменения кода:

```bash
docker-compose down
docker-compose up -d --build
```

## Troubleshooting

### Проблема: Бот не запускается

```bash
# Проверьте логи
docker-compose logs

# Проверьте что .env файл существует и заполнен
cat .env
```

### Проблема: База данных не сохраняется

Убедитесь, что файл `goszakup.db` существует в корне проекта или создайте его:

```bash
touch goszakup.db
```

### Проблема: Нет доступа к Google Sheets

Проверьте что файл `credentials/google_service_account.json` существует и `GOOGLE_SHEETS_ENABLED=true` в `.env`.

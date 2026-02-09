#!/bin/bash
# Скрипт для очистки временных файлов

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🧹 Очистка временных файлов..."

# Удалить macOS файлы
echo "  - Удаление .DS_Store и ._* файлов..."
find . -name ".DS_Store" -type f -delete
find . -name "._*" -type f -delete

# Удалить Python cache
echo "  - Удаление __pycache__ и .pyc файлов..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete

# Удалить временные Claude файлы
echo "  - Удаление tmpclaude-* файлов..."
rm -f tmpclaude-*

# Очистить старые логи (оставить последние 7)
echo "  - Очистка старых логов..."
cd logs/
ls -t *.log 2>/dev/null | tail -n +8 | xargs rm -f 2>/dev/null
cd ..

echo "✅ Очистка завершена!"

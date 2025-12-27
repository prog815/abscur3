#!/bin/bash
# Скрипт запуска тестирования Frankfurter.app

echo "Запуск тестирования Frankfurter.app для AbsCur3..."
echo "Дата: $(date)"

cd "$(dirname "$0")"

# Создаем виртуальное окружение (опционально)
if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активируем и устанавливаем зависимости
source venv/bin/activate
pip install requests > /dev/null 2>&1

# Запускаем тест
python test_coverage.py

deactivate

echo "Тестирование завершено!"
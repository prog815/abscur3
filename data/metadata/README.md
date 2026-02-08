# Метаданные проекта AbsCur3

## Описание файлов

### currency_pairs.json
Простой массив с именами всех валютных пар в формате `AAA_BBB`.

### currency_pairs_full.json
Полная информация о каждой валютной паре:
- `symbol`: имя пары в формате `AAA_BBB`
- `original_symbol`: исходное имя пары в формате `AAA/BBB`
- `currency_group`: группа валюты (Major/Minor/Exotic)
- `currency_base`: базовая валюта
- `currency_quote`: котируемая валюта

### currency_stats.json
Статистика по валютам:
- Общее количество пар
- Количество пар по группам
- Примеры пар

## Обновление
Данные автоматически обновляются при изменении `config/currencies.py`.
Запустите скрипт `scripts/create_currency_pairs_json.py` для обновления.

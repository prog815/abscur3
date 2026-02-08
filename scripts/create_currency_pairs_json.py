"""
Скрипт для создания JSON-файла со списком валютных пар из config/currencies.py.
Создает файл data/metadata/currency_pairs.json для использования в Kaggle Notebook и других инструментах.
"""

import json
import os
import sys

# Добавляем корень репозитория в путь Python для импорта config.currencies
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_currency_pairs_json():
    """Создает JSON-файл со списком валютных пар"""
    
    try:
        # Импортируем конфигурацию валютных пар
        from config.currencies import CURRENCY_PAIRS
        
        print(f"Успешно загружен список из {len(CURRENCY_PAIRS)} валютных пар")
        
        # Преобразуем формат пар из "AAA/BBB" в "AAA_BBB"
        formatted_pairs = []
        for pair_info in CURRENCY_PAIRS:
            symbol = pair_info[0]  # формат "AAA/BBB"
            formatted_symbol = symbol.replace("/", "_")  # формат "AAA_BBB"
            formatted_pairs.append(formatted_symbol)
        
        # Создаем полную информацию о парах
        full_pairs_info = []
        for pair_info in CURRENCY_PAIRS:
            symbol, group, base, quote = pair_info
            formatted_symbol = symbol.replace("/", "_")
            full_pairs_info.append({
                "symbol": formatted_symbol,
                "original_symbol": symbol,
                "currency_group": group,
                "currency_base": base,
                "currency_quote": quote
            })
        
        # Создаем директорию если она не существует
        metadata_dir = os.path.join("data", "metadata")
        os.makedirs(metadata_dir, exist_ok=True)
        
        # Сохраняем простой список пар
        simple_pairs_path = os.path.join(metadata_dir, "currency_pairs.json")
        with open(simple_pairs_path, "w", encoding="utf-8") as f:
            json.dump(formatted_pairs, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Создан файл {simple_pairs_path} с {len(formatted_pairs)} парами")
        print(f"  Пример первых 5 пар: {formatted_pairs[:5]}")
        
        # Сохраняем полную информацию о парах
        full_info_path = os.path.join(metadata_dir, "currency_pairs_full.json")
        with open(full_info_path, "w", encoding="utf-8") as f:
            json.dump(full_pairs_info, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Создан файл {full_info_path} с полной информацией о {len(full_pairs_info)} парах")
        
        # Также создаем файл со статистикой
        stats = {
            "total_pairs": len(formatted_pairs),
            "major_pairs_count": len([p for p in full_pairs_info if p["currency_group"] == "Major"]),
            "minor_pairs_count": len([p for p in full_pairs_info if p["currency_group"] == "Minor"]),
            "exotic_pairs_count": len([p for p in full_pairs_info if p["currency_group"] == "Exotic"]),
            "pairs_sample": formatted_pairs[:10],
            "created_at": str(sys.modules[__name__].__file__)
        }
        
        stats_path = os.path.join(metadata_dir, "currency_stats.json")
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Создан файл {stats_path} со статистикой")
        
        # Создаем README файл для директории metadata
        readme_path = os.path.join(metadata_dir, "README.md")
        readme_content = """# Метаданные проекта AbsCur3

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
"""
        
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        
        print(f"✓ Создан файл {readme_path}")
        
        return True
        
    except ImportError as e:
        print(f"✗ Ошибка импорта config.currencies: {e}")
        print("Убедитесь, что запускаете скрипт из корня репозитория")
        return False
    except Exception as e:
        print(f"✗ Неожиданная ошибка: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Создание JSON-файлов со списком валютных пар")
    print("=" * 60)
    
    success = create_currency_pairs_json()
    
    print("=" * 60)
    if success:
        print("✅ Все файлы успешно созданы!")
        print("Теперь можно использовать в Kaggle Notebook:")
        print("https://prog815.github.io/abscur3/data/metadata/currency_pairs.json")
    else:
        print("❌ Создание файлов завершилось с ошибкой")
    print("=" * 60)
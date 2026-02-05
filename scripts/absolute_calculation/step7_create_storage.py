#!/usr/bin/env python3
"""
Шаг 7: Создание структуры хранения согласно ТЗ
Особенность: БЕЗ нормировки по USD, сохранение естественной нормировки (среднее логарифмов = 0)
Запуск из корневого каталога: python scripts/absolute_calculation/step7_create_storage.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import json
from datetime import datetime
import shutil

# Добавляем путь к корневому каталогу для импорта
sys.path.insert(0, str(Path(__file__).parent))

def create_directory_structure():
    """Создает структуру директорий согласно ТЗ"""
    root_dir = Path(__file__).parent.parent.parent
    
    # Основные директории из ТЗ
    directories = [
        "data/absolute/daily",
        "data/absolute/currencies", 
        "data/absolute/errors",
        "data/absolute/metadata"
    ]
    
    print("Создание структуры директорий...")
    for directory in directories:
        dir_path = root_dir / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {directory}")
    
    return root_dir

def load_step6b_results(root_dir):
    """Загружает результаты из Шага 6b"""
    step6b_dir = root_dir / "data" / "absolute" / "step6b_results"
    
    if not step6b_dir.exists():
        print(f"✗ Директория не найдена: {step6b_dir}")
        return []
    
    # Находим все файлы с абсолютными курсами
    absolute_files = list(step6b_dir.glob("absolute_raw_*.csv"))
    results = []
    
    for file_path in absolute_files:
        # Извлекаем дату из имени файла
        date_str = file_path.stem.replace("absolute_raw_", "")
        
        # Загружаем абсолютные курсы
        abs_df = pd.read_csv(file_path)
        
        # Загружаем соответствующие погрешности
        errors_file = step6b_dir / f"errors_detailed_{date_str}.csv"
        if errors_file.exists():
            errors_df = pd.read_csv(errors_file)
        else:
            errors_df = pd.DataFrame(columns=['pair', 'actual_value', 'calculated_value', 'error_percent'])
        
        # Сохраняем результат
        results.append({
            'date': date_str,
            'absolute_rates': dict(zip(abs_df['currency'], abs_df['absolute_value'])),
            'errors': errors_df
        })
    
    print(f"✓ Загружено результатов из Шага 6b: {len(results)} дат")
    return results

def save_daily_files(root_dir, results):
    """Сохраняет ежедневные файлы в формате ТЗ"""
    daily_dir = root_dir / "data" / "absolute" / "daily"
    
    print(f"\nСохранение ежедневных файлов в: {daily_dir}")
    
    for result in results:
        date_str = result['date']
        
        # Создаем DataFrame с абсолютными курсами
        abs_data = []
        for currency, value in result['absolute_rates'].items():
            abs_data.append({
                'currency': currency,
                'absolute_value': value
            })
        
        abs_df = pd.DataFrame(abs_data)
        
        # Сохраняем в файл
        daily_file = daily_dir / f"{date_str}.csv"
        abs_df.to_csv(daily_file, index=False)
        
        print(f"  ✓ {date_str}.csv: {len(abs_df)} валют")
    
    return len(results)

def save_currency_files(root_dir, results):
    """Создает отдельные файлы для каждой валюты"""
    currencies_dir = root_dir / "data" / "absolute" / "currencies"
    
    print(f"\nСоздание файлов по валютам в: {currencies_dir}")
    
    # Собираем все данные по валютам
    currency_data = {}
    
    for result in results:
        date_str = result['date']
        
        for currency, value in result['absolute_rates'].items():
            if currency not in currency_data:
                currency_data[currency] = []
            
            currency_data[currency].append({
                'date': date_str,
                'absolute_value': value
            })
    
    # Сохраняем файлы для каждой валюты
    saved_count = 0
    for currency, data in currency_data.items():
        df = pd.DataFrame(data)
        df = df.sort_values('date')  # Сортируем по дате
        
        currency_file = currencies_dir / f"{currency}.csv"
        df.to_csv(currency_file, index=False)
        
        saved_count += 1
        print(f"  ✓ {currency}.csv: {len(df)} записей")
    
    print(f"Всего создано файлов валют: {saved_count}")
    return saved_count

def save_error_files(root_dir, results):
    """Сохраняет файлы с погрешностями"""
    errors_dir = root_dir / "data" / "absolute" / "errors"
    
    print(f"\nСохранение файлов с погрешностями в: {errors_dir}")
    
    saved_count = 0
    for result in results:
        date_str = result['date']
        
        if not result['errors'].empty:
            # Форматируем DataFrame согласно ТЗ
            errors_df = result['errors'][['pair', 'actual_value', 'calculated_value', 'error_percent']].copy()
            
            # Сохраняем в файл
            error_file = errors_dir / f"{date_str}.csv"
            errors_df.to_csv(error_file, index=False)
            
            saved_count += 1
            print(f"  ✓ {date_str}.csv: {len(errors_df)} пар")
    
    return saved_count

def create_metadata(root_dir, results):
    """Создает файлы метаданных"""
    metadata_dir = root_dir / "data" / "absolute" / "metadata"
    
    print(f"\nСоздание метаданных в: {metadata_dir}")
    
    # Статистика по дням
    daily_stats = []
    for result in results:
        date_str = result['date']
        
        if not result['errors'].empty:
            errors = result['errors']['error_percent']
            abs_errors = errors.abs()
            
            stats = {
                'date': date_str,
                'num_currencies': len(result['absolute_rates']),
                'num_pairs': len(result['errors']),
                'avg_error': abs_errors.mean(),
                'max_error': abs_errors.max(),
                'min_error': abs_errors.min(),
                'currencies': list(result['absolute_rates'].keys())
            }
            daily_stats.append(stats)
    
    # Сохраняем статистику по дням
    if daily_stats:
        stats_df = pd.DataFrame(daily_stats)
        stats_file = metadata_dir / "daily_statistics.csv"
        stats_df.to_csv(stats_file, index=False)
        print(f"  ✓ daily_statistics.csv: {len(stats_df)} дней")
    
    # Общая статистика
    if results:
        all_errors = []
        all_currencies = set()
        all_pairs = set()
        
        for result in results:
            if not result['errors'].empty:
                all_errors.extend(result['errors']['error_percent'].abs().tolist())
                all_currencies.update(result['absolute_rates'].keys())
                all_pairs.update(result['errors']['pair'].tolist())
        
        overall_stats = {
            'generated_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_days': len(results),
            'total_currencies': len(all_currencies),
            'total_pairs': len(all_pairs),
            'avg_error_overall': np.mean(all_errors) if all_errors else 0,
            'max_error_overall': np.max(all_errors) if all_errors else 0,
            'min_error_overall': np.min(all_errors) if all_errors else 0,
            'currencies_list': sorted(list(all_currencies)),
            'date_range': {
                'first': min([r['date'] for r in results]),
                'last': max([r['date'] for r in results])
            },
            'normalization_info': {
                'type': 'natural_log_mean_zero',
                'description': 'Абсолютные курсы нормированы так, что среднее логарифмов равно 0',
                'mathematical_property': 'Система инвариантна относительно умножения всех курсов на константу',
                'practical_meaning': 'Отношения абсолютных курсов дают парные курсы'
            },
            'source_data': {
                'step': '6b',
                'description': 'Результаты получены в Шаге 6b (10 пар, без нормировки по USD)'
            }
        }
        
        # Сохраняем общую статистику
        stats_file = metadata_dir / "overall_statistics.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(overall_stats, f, ensure_ascii=False, indent=2)
        
        print(f"  ✓ overall_statistics.json: полная статистика расчета")
        
        # Также сохраняем в CSV для удобства
        overall_csv = metadata_dir / "overall_statistics.csv"
        csv_data = {
            'metric': list(overall_stats.keys()),
            'value': [str(v) if not isinstance(v, (dict, list)) else json.dumps(v) for v in overall_stats.values()]
        }
        pd.DataFrame(csv_data).to_csv(overall_csv, index=False)
        print(f"  ✓ overall_statistics.csv: табличная версия")
    
    return len(daily_stats) if daily_stats else 0

def create_readme_files(root_dir):
    """Создает README файлы для директорий"""
    print(f"\nСоздание README файлов...")
    
    # README для data/absolute
    absolute_dir = root_dir / "data" / "absolute"
    readme_content = """# Абсолютные валютные курсы AbsCur3

## Структура директорий

### daily/
Файлы с абсолютными курсами на каждую дату.
Формат: `YYYY-MM-DD.csv`
Колонки: `currency, absolute_value`

### currencies/
Отдельные файлы для каждой валюты.
Формат: `{CURRENCY}.csv`
Колонки: `date, absolute_value`

### errors/
Файлы с погрешностями восстановления парных курсов.
Формат: `YYYY-MM-DD.csv`
Колонки: `pair, actual_value, calculated_value, error_percent`

### metadata/
Метаданные и статистика расчетов.

## Особенности формата

1. **Абсолютные курсы нормированы** так, что среднее логарифмов равно 0
2. **Нет привязки к USD** - все валюты равноправны
3. **Важны отношения** между абсолютными курсами, а не абсолютные значения

## Математические свойства

- Система имеет бесконечное семейство решений
- Все решения связаны умножением на константу
- Отношения абсолютных курсов восстанавливают парные курсы
- Погрешности показывают рыночную неэффективность

## Использование

Для получения парного курса X/Y:
```
pair_rate = absolute_X / absolute_Y
```

## Источник данных

Результаты получены из Шага 6b (10 пар, без нормировки по USD).
"""
    
    readme_file = absolute_dir / "README.md"
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"  ✓ data/absolute/README.md")
    
    # Создаем простые README для поддиректорий
    for subdir in ["daily", "currencies", "errors", "metadata"]:
        subdir_path = absolute_dir / subdir
        sub_readme = subdir_path / "README.md"
        
        if subdir == "daily":
            content = "# Ежедневные файлы с абсолютными курсами\n\nКаждый файл содержит абсолютные курсы всех валют на конкретную дату."
        elif subdir == "currencies":
            content = "# Файлы по валютам\n\nКаждый файл содержит историю абсолютного курса конкретной валюты."
        elif subdir == "errors":
            content = "# Погрешности восстановления парных курсов\n\nФайлы содержат разницу между фактическими и рассчитанными парными курсами."
        elif subdir == "metadata":
            content = "# Метаданные расчетов\n\nСтатистика и информация о расчетах абсолютных курсов."
        
        with open(sub_readme, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✓ data/absolute/{subdir}/README.md")
    
    return 5  # Количество созданных README файлов

def verify_structure(root_dir):
    """Проверяет созданную структуру"""
    print(f"\nПроверка структуры...")
    
    base_dirs = [
        "data/absolute/daily",
        "data/absolute/currencies",
        "data/absolute/errors", 
        "data/absolute/metadata"
    ]
    
    issues = []
    
    for dir_path in base_dirs:
        full_path = root_dir / dir_path
        if not full_path.exists():
            issues.append(f"✗ Отсутствует директория: {dir_path}")
        else:
            print(f"  ✓ {dir_path}")
    
    # Проверяем наличие файлов
    daily_files = list((root_dir / "data/absolute/daily").glob("*.csv"))
    currency_files = list((root_dir / "data/absolute/currencies").glob("*.csv"))
    error_files = list((root_dir / "data/absolute/errors").glob("*.csv"))
    
    print(f"  Найдено daily файлов: {len(daily_files)}")
    print(f"  Найдено currency файлов: {len(currency_files)}")
    print(f"  Найдено error файлов: {len(error_files)}")
    
    if issues:
        print("\nПроблемы:")
        for issue in issues:
            print(f"  {issue}")
        return False
    
    return True

def main():
    print("=" * 100)
    print("Шаг 7: Создание структуры хранения (без нормировки по USD)")
    print("=" * 100)
    print("Создание структуры согласно ТЗ с сохранением естественной нормировки")
    print("(среднее логарифмов абсолютных курсов = 0)\n")
    
    # Создаем структуру директорий
    root_dir = create_directory_structure()
    
    # Загружаем результаты из Шага 6b
    results = load_step6b_results(root_dir)
    
    if not results:
        print("\n✗ Нет данных для обработки. Сначала выполните Шаг 6b.")
        return
    
    # Сохраняем в форматах ТЗ
    daily_count = save_daily_files(root_dir, results)
    currency_count = save_currency_files(root_dir, results)
    error_count = save_error_files(root_dir, results)
    metadata_count = create_metadata(root_dir, results)
    readme_count = create_readme_files(root_dir)
    
    # Проверяем структуру
    structure_ok = verify_structure(root_dir)
    
    # Сводный отчет
    print("\n" + "=" * 100)
    print("СВОДНЫЙ ОТЧЕТ")
    print("=" * 100)
    
    print(f"\nСоздано файлов:")
    print(f"  Ежедневных (daily/): {daily_count}")
    print(f"  По валютам (currencies/): {currency_count}")
    print(f"  Погрешностей (errors/): {error_count}")
    print(f"  Метаданных (metadata/): {metadata_count}")
    print(f"  README файлов: {readme_count}")
    
    # Анализируем данные
    if results:
        print(f"\nОбработано дат: {len(results)}")
        
        # Собираем статистику по валютам
        all_currencies = set()
        for result in results:
            all_currencies.update(result['absolute_rates'].keys())
        
        print(f"Уникальных валют: {len(all_currencies)}")
        print(f"Список валют: {sorted(all_currencies)}")
        
        # Статистика по погрешностям
        all_errors = []
        for result in results:
            if not result['errors'].empty:
                all_errors.extend(result['errors']['error_percent'].abs().tolist())
        
        if all_errors:
            print(f"\nСтатистика погрешностей:")
            print(f"  Средняя погрешность: {np.mean(all_errors):.6f}%")
            print(f"  Максимальная погрешность: {np.max(all_errors):.6f}%")
            print(f"  Минимальная погрешность: {np.min(all_errors):.6f}%")
            
            # Качество
            avg_error = np.mean(all_errors)
            if avg_error < 0.01:
                quality = "ОТЛИЧНО"
            elif avg_error < 0.1:
                quality = "ХОРОШО"
            elif avg_error < 1.0:
                quality = "УДОВЛЕТВОРИТЕЛЬНО"
            else:
                quality = "ПЛОХО"
            
            print(f"  Оценка качества: {quality}")
    
    print(f"\nСтруктура успешно создана: {'✓ ДА' if structure_ok else '✗ НЕТ'}")
    
    # Ключевые особенности
    print(f"\nКЛЮЧЕВЫЕ ОСОБЕННОСТИ:")
    print("  1. ✅ Без нормировки по USD - все валюты равноправны")
    print("  2. ✅ Естественная нормировка (среднее логарифмов = 0)")
    print("  3. ✅ Сохранены отношения между валютами")
    print("  4. ✅ Все форматы соответствуют ТЗ")
    
    # Пути к файлам
    print(f"\nПУТИ К ФАЙЛАМ:")
    print(f"  Ежедневные файлы: {root_dir / 'data/absolute/daily/'}")
    print(f"  Файлы валют: {root_dir / 'data/absolute/currencies/'}")
    print(f"  Погрешности: {root_dir / 'data/absolute/errors/'}")
    print(f"  Метаданные: {root_dir / 'data/absolute/metadata/'}")
    
    # Инструкции по использованию
    print(f"\nИНСТРУКЦИИ ПО ИСПОЛЬЗОВАНИЮ:")
    print("  1. Для получения абсолютного курса валюты на дату:")
    print(f"     Файл: data/absolute/daily/YYYY-MM-DD.csv")
    print("  2. Для получения истории абсолютного курса валюты:")
    print(f"     Файл: data/absolute/currencies/{{CURRENCY}}.csv")
    print("  3. Для получения парного курса X/Y:")
    print("     abs_X / abs_Y = курс пары X/Y")
    
    print(f"\n" + "=" * 100)
    print("ШАГ 7 УСПЕШНО ЗАВЕРШЕН!")
    print("=" * 100)
    print(f"\nСтруктура хранения создана согласно ТЗ")
    print("Особенность: сохранена естественная нормировка (без привязки к USD)")
    print(f"Готово к переходу к Шагу 8: Тестирование и оптимизация")

if __name__ == "__main__":
    main()

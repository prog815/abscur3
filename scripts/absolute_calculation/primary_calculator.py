#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
primary_calculator.py – Шаг 2.2: Реализация функции загрузки данных с обработкой OHLC.
Функциональность:
- load_pair_data_raw() – загрузка одной пары, переименование datetime→date, close→rate
- Кеширование загруженных DataFrame для повторного использования
- Демонстрация работы на примере EURUSD, USDJPY, GBPUSD
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

# ---------- Конфигурация путей (относительно корня проекта) ----------
PAIRS_JSON = Path("data/metadata/currency_pairs.json")
DATA_DIR = Path("data/raw/twelve_data/pairs")
CORE_CURRENCIES = {'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD'}

# ---------- Кеш для загруженных данных ----------
_DATA_CACHE = {}

def convert_to_filename(pair):
    """Преобразует EUR_USD → EURUSD.csv."""
    return pair.replace("_", "") + ".csv"

def load_pair_data_raw(pair_name, use_cache=True, force_reload=False):
    """
    Загружает данные по валютной паре из data/raw/twelve_data/pairs/.
    
    Параметры:
        pair_name (str): имя пары в формате 'EUR_USD'.
        use_cache (bool): использовать кеш (по умолчанию True).
        force_reload (bool): игнорировать кеш и перезагрузить данные.
    
    Возвращает:
        pd.DataFrame | None: DataFrame с колонками ['date', 'rate'] (и только они),
                             отсортированный по дате. Если файл отсутствует – None.
    """
    # 1. Преобразование имени и формирование пути
    filename = convert_to_filename(pair_name)
    filepath = DATA_DIR / filename
    
    # 2. Проверка существования файла
    if not filepath.exists():
        print(f"⚠️  Файл не найден: {filepath} (пара {pair_name})")
        return None
    
    # 3. Кеш
    cache_key = pair_name
    if use_cache and not force_reload and cache_key in _DATA_CACHE:
        return _DATA_CACHE[cache_key].copy()
    
    # 4. Загрузка CSV
    try:
        # Читаем только нужные колонки, чтобы экономить память
        df = pd.read_csv(filepath, usecols=['datetime', 'close'])
    except Exception as e:
        print(f"❌ Ошибка загрузки {filepath.name}: {e}")
        return None
    
    # 5. Переименование колонок
    df.rename(columns={'datetime': 'date', 'close': 'rate'}, inplace=True)
    
    # 6. Преобразование типов
    df['date'] = pd.to_datetime(df['date'])
    df['rate'] = pd.to_numeric(df['rate'], errors='coerce')
    
    # 7. Удаление строк с некорректными курсами (NaN)
    df.dropna(subset=['rate'], inplace=True)
    
    # 8. Сортировка и сброс индекса
    df.sort_values('date', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    # 9. Сохраняем в кеш
    if use_cache:
        _DATA_CACHE[cache_key] = df.copy()
    
    return df

def demo_load_pair_data():
    """Демонстрация работы функции загрузки на нескольких парах."""
    print("\n" + "=" * 60)
    print(" ДЕМОНСТРАЦИЯ: load_pair_data_raw()")
    print("=" * 60)
    
    test_pairs = ['EUR_USD', 'USD_JPY', 'GBP_USD', 'XXX_YYY']  # последняя не существует
    
    for pair in test_pairs:
        df = load_pair_data_raw(pair)
        if df is not None:
            print(f"\n✅ {pair}:")
            print(f"   - Строк: {len(df)}")
            print(f"   - Диапазон: {df['date'].min().date()} – {df['date'].max().date()}")
            print(f"   - Последние 3 курса (rate):")
            print(df[['date', 'rate']].tail(3).to_string(index=False, header=False))
        else:
            print(f"\n❌ {pair}: данные не загружены")
    
    # Проверка кеша (просто демонстрация, что при повторном вызове ошибок нет)
    print("\n--- Проверка кеша ---")
    for pair in ['EUR_USD', 'USD_JPY']:
        df1 = load_pair_data_raw(pair, use_cache=False)  # принудительная загрузка
        df2 = load_pair_data_raw(pair, use_cache=True)   # из кеша
        print(f"{pair}: загружено из кеша: {df2 is not None}")
    
    # Статистика по кешу
    print(f"\n📦 Кеш содержит {len(_DATA_CACHE)} пар: {list(_DATA_CACHE.keys())}")

# ---------- Существующая функция load_pairs_list() и check_files_exist() ----------
def load_pairs_list():
    """Загружает список валютных пар из JSON."""
    if not PAIRS_JSON.exists():
        raise FileNotFoundError(f"Файл не найден: {PAIRS_JSON}")
    with open(PAIRS_JSON, 'r', encoding='utf-8') as f:
        pairs = json.load(f)
    print(f"✅ Загружено пар из JSON: {len(pairs)}")
    return pairs

def check_files_exist(pairs, data_dir):
    """Проверяет существование CSV-файлов для каждой пары."""
    existing = []
    missing = []
    for pair in pairs:
        filename = convert_to_filename(pair)
        filepath = data_dir / filename
        if filepath.exists():
            existing.append((pair, filepath))
        else:
            missing.append((pair, filepath))
    print(f"📁 Существующих файлов: {len(existing)}")
    print(f"❌ Отсутствует файлов: {len(missing)}")
    return existing, missing

def get_date_range_from_file(filepath, nrows=1000):
    """
    Быстро определяет минимальную и максимальную дату в CSV.
    Читает только столбец 'datetime', ограничиваясь первыми nrows строками.
    """
    try:
        df = pd.read_csv(filepath, usecols=['datetime'], nrows=nrows)
        df['datetime'] = pd.to_datetime(df['datetime'])
        min_date = df['datetime'].min()
        max_date = df['datetime'].max()
        return min_date, max_date
    except Exception as e:
        print(f"⚠️  Ошибка при чтении {filepath.name}: {e}")
        return None, None

def main():
    print("=" * 60)
    print(" ШАГ 2.1 – Адаптация каркаса под реальную структуру данных")
    print("=" * 60)
    # ... (весь код из шага 2.1, он уже есть) ...
    # Для краткости я оставляю многоточие, но вы должны сохранить ранее написанный код main().
    # Ниже добавлен вызов демонстрации шага 2.2.
    
    # После завершения основной части шага 2.1 вызываем демонстрацию новой функции
    demo_load_pair_data()

if __name__ == "__main__":
    main()
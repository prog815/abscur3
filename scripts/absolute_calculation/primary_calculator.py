#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
primary_calculator.py – Шаг 2.3: Реализация расширенного заполнения пропусков.
Функциональность:
- fill_missing_prices() – заполнение пропусков forward fill с limit=30 дней.
- Демонстрация на проблемных парах (AED_USD, AFN_USD, ARS_USD) и основных.
- Создание словаря filled_prices_dict для тестовых пар.
- Только текстовая статистика, без графиков.
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

# ---------- Конфигурация путей ----------
PAIRS_JSON = Path("data/metadata/currency_pairs.json")
DATA_DIR = Path("data/raw/twelve_data/pairs")
CORE_CURRENCIES = {'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD'}

# ---------- Кеш для загруженных данных ----------
_DATA_CACHE = {}

# ---------- Преобразование имени файла ----------
def convert_to_filename(pair):
    """Преобразует EUR_USD → EURUSD.csv."""
    return pair.replace("_", "") + ".csv"

# ---------- Загрузка одной пары (шаг 2.2) ----------
def load_pair_data_raw(pair_name, use_cache=True, force_reload=False):
    """Загружает данные по валютной паре. Возвращает df с колонками date, rate."""
    filename = convert_to_filename(pair_name)
    filepath = DATA_DIR / filename
    
    if not filepath.exists():
        print(f"⚠️  Файл не найден: {filepath} (пара {pair_name})")
        return None
    
    cache_key = pair_name
    if use_cache and not force_reload and cache_key in _DATA_CACHE:
        return _DATA_CACHE[cache_key].copy()
    
    try:
        df = pd.read_csv(filepath, usecols=['datetime', 'close'])
    except Exception as e:
        print(f"❌ Ошибка загрузки {filepath.name}: {e}")
        return None
    
    df.rename(columns={'datetime': 'date', 'close': 'rate'}, inplace=True)
    df['date'] = pd.to_datetime(df['date'])
    df['rate'] = pd.to_numeric(df['rate'], errors='coerce')
    df.dropna(subset=['rate'], inplace=True)
    df.sort_values('date', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    if use_cache:
        _DATA_CACHE[cache_key] = df.copy()
    
    return df

# ---------- Заполнение пропусков (шаг 2.3) ----------
def fill_missing_prices(series, full_date_index, lookback_days=30):
    """
    Заполняет пропуски во временном ряду методом forward fill с ограничением.
    
    Параметры:
        series (pd.Series): исходный ряд с индексом DatetimeIndex (значения rate).
        full_date_index (pd.DatetimeIndex): полный календарный индекс дат.
        lookback_days (int): максимальное количество дней для переноса значения.
    
    Возвращает:
        pd.Series: заполненный ряд, индексированный по full_date_index.
    """
    filled = series.reindex(full_date_index)
    filled = filled.ffill(limit=lookback_days)
    return filled

def analyze_missing(original_df, pair_name, lookback=30):
    """
    Анализирует пропуски в данных пары и выводит текстовую статистику.
    Возвращает словарь со статистикой и заполненный ряд (для всего диапазона).
    """
    original_series = original_df.set_index('date')['rate']
    full_index = pd.date_range(original_df['date'].min(), original_df['date'].max(), freq='D')
    filled_series = fill_missing_prices(original_series, full_index, lookback_days=lookback)
    
    orig_dates = set(original_series.index)
    full_dates = set(full_index)
    missing_dates = full_dates - orig_dates
    filled_dates = filled_series[filled_series.notna()].index
    newly_filled = filled_dates.intersection(missing_dates)
    
    # Вычисляем максимальный разрыв с помощью numpy (быстрее и корректнее)
    orig_sorted = np.array(sorted(original_series.index))
    if len(orig_sorted) > 1:
        gaps = (orig_sorted[1:] - orig_sorted[:-1]).astype('timedelta64[D]').astype(int)
        max_gap = gaps.max()
    else:
        max_gap = 0
        gaps = np.array([])
    
    print(f"\n📊 Статистика пропусков для {pair_name}:")
    print(f"   - Всего дат в диапазоне: {len(full_index)}")
    print(f"   - Исходных записей: {len(original_series)}")
    print(f"   - Пропущенных дат: {len(missing_dates)} ({len(missing_dates)/len(full_index)*100:.1f}%)")
    print(f"   - Заполнено (limit={lookback}): {len(newly_filled)}")
    print(f"   - Максимальный разрыв (дней): {max_gap}")
    
    if len(gaps) > 0:
        unfilled = gaps[gaps > lookback]
        if len(unfilled) > 0:
            print(f"   - Разрывов > {lookback} дней: {len(unfilled)} (макс: {unfilled.max()})")
        else:
            print(f"   - Разрывов > {lookback} дней: нет")
    
    return {
        'pair': pair_name,
        'total_days': len(full_index),
        'original_count': len(original_series),
        'missing_count': len(missing_dates),
        'filled_count': len(newly_filled),
        'max_gap_days': max_gap
    }, filled_series

def demo_fill_missing():
    """Демонстрация работы функции заполнения пропусков на проблемных парах."""
    print("\n" + "=" * 60)
    print(" ШАГ 2.3 – Заполнение пропусков (lookback=30 дней)")
    print("=" * 60)
    
    # Проблемные пары (по отчёту Kaggle) + EUR_USD для сравнения
    test_pairs = ['AED_USD', 'AFN_USD', 'ARS_USD', 'EUR_USD']
    
    filled_prices_dict = {}
    stats_list = []
    
    for pair in test_pairs:
        df = load_pair_data_raw(pair)
        if df is not None:
            stats, filled = analyze_missing(df, pair, lookback=30)
            stats_list.append(stats)
            filled_prices_dict[pair] = filled
    
    # Сводная таблица
    print("\n📋 Сводная статистика по заполнению пропусков:")
    stats_df = pd.DataFrame(stats_list)
    print(stats_df.to_string(index=False))
    
    print(f"\n📦 Словарь filled_prices_dict содержит {len(filled_prices_dict)} пар: {list(filled_prices_dict.keys())}")
    return filled_prices_dict

# ---------- Существующие функции (шаги 2.1, 2.2) ----------
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
    """Быстро определяет мин и макс дату в CSV."""
    try:
        df = pd.read_csv(filepath, usecols=['datetime'], nrows=nrows)
        df['datetime'] = pd.to_datetime(df['datetime'])
        min_date = df['datetime'].min()
        max_date = df['datetime'].max()
        return min_date, max_date
    except Exception as e:
        print(f"⚠️  Ошибка при чтении {filepath.name}: {e}")
        return None, None

def demo_load_pair_data():
    """Демонстрация работы функции загрузки (шаг 2.2)."""
    print("\n" + "=" * 60)
    print(" ДЕМОНСТРАЦИЯ: load_pair_data_raw()")
    print("=" * 60)
    
    test_pairs = ['EUR_USD', 'USD_JPY', 'GBP_USD', 'XXX_YYY']
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
    
    print("\n--- Проверка кеша ---")
    for pair in ['EUR_USD', 'USD_JPY']:
        df1 = load_pair_data_raw(pair, use_cache=False)
        df2 = load_pair_data_raw(pair, use_cache=True)
        print(f"{pair}: загружено из кеша: {df2 is not None}")
    
    print(f"\n📦 Кеш содержит {len(_DATA_CACHE)} пар: {list(_DATA_CACHE.keys())}")

def main():
    print("=" * 60)
    print(" ШАГ 2.1 – Адаптация каркаса под реальную структуру данных")
    print("=" * 60)
    
    pairs = load_pairs_list()
    existing_pairs, missing_pairs = check_files_exist(pairs, DATA_DIR)
    
    print("\n🔁 Примеры преобразования имён (первые 5):")
    for pair in pairs[:5]:
        print(f"   {pair:12} → {convert_to_filename(pair)}")
    
    print("\n📅 Анализ дат (первые 10 существующих файлов):")
    global_min = None
    global_max = None
    for idx, (pair, filepath) in enumerate(existing_pairs[:10]):
        min_dt, max_dt = get_date_range_from_file(filepath)
        if min_dt and max_dt:
            print(f"   {pair:12} : {min_dt.date()} – {max_dt.date()}  ({filepath.name})")
            if global_min is None or min_dt < global_min:
                global_min = min_dt
            if global_max is None or max_dt > global_max:
                global_max = max_dt
    
    if global_min and global_max:
        print("\n🌍 Ориентировочный общий диапазон дат (по первым 10 файлам):")
        print(f"   С: {global_min.date()}  По: {global_max.date()}")
    
    all_currencies = set()
    for pair in pairs:
        base, quote = pair.split('_')
        all_currencies.add(base)
        all_currencies.add(quote)
    print(f"\n💰 Уникальных валют (всего): {len(all_currencies)}")
    core_available = all_currencies.intersection(CORE_CURRENCIES)
    print(f"   Ядро валют (USD,EUR,GBP,JPY,CHF,CAD,AUD):")
    print(f"   Доступно: {sorted(core_available)}")
    print(f"   Отсутствует: {sorted(CORE_CURRENCIES - core_available)}")
    
    # Шаг 2.2
    demo_load_pair_data()
    
    # Шаг 2.3
    demo_fill_missing()
    
    print("\n✅ Шаг 2.3 завершён.")

if __name__ == "__main__":
    main()
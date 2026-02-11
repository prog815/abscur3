#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
primary_calculator.py – Первичный расчёт абсолютных курсов AbsCur3
Финальная версия с шагом 2.5a:
- Загрузка и заполнение всех 287 пар
- Построение availability_df, поиск T_start = 1979-12-24
- Формирование списка ВСЕХ дат для расчёта (без фильтрации)
- Подготовка к шагу 2.6 (ядро МНК)
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

# ---------- tqdm для прогресс-баров ----------
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("⚠️  tqdm не установлен. Рекомендуется: pip install tqdm")

# ---------- Конфигурация путей ----------
PAIRS_JSON = Path("data/metadata/currency_pairs.json")
DATA_DIR = Path("data/raw/twelve_data/pairs")
CORE_CURRENCIES = {'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD'}
METADATA_DIR = Path("data/absolute/metadata")
METADATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------- Кеш для загруженных данных ----------
_DATA_CACHE = {}

# ---------- Преобразование имени файла ----------
def convert_to_filename(pair):
    """EUR_USD → EURUSD.csv."""
    return pair.replace("_", "") + ".csv"

# ---------- Загрузка одной пары (шаг 2.2) ----------
def load_pair_data_raw(pair_name, use_cache=True, force_reload=False):
    """Загружает данные пары, возвращает df с колонками date, rate."""
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
    """Forward fill с ограничением."""
    filled = series.reindex(full_date_index)
    filled = filled.ffill(limit=lookback_days)
    return filled

def analyze_missing(original_df, pair_name, lookback=30):
    """Анализ пропусков, возвращает статистику и заполненный ряд."""
    original_series = original_df.set_index('date')['rate']
    full_index = pd.date_range(original_df['date'].min(), original_df['date'].max(), freq='D')
    filled_series = fill_missing_prices(original_series, full_index, lookback)

    orig_dates = set(original_series.index)
    full_dates = set(full_index)
    missing_dates = full_dates - orig_dates
    filled_dates = filled_series[filled_series.notna()].index
    newly_filled = filled_dates.intersection(missing_dates)

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
    """Демонстрация шага 2.3."""
    print("\n" + "=" * 60)
    print(" ШАГ 2.3 – Заполнение пропусков (lookback=30 дней)")
    print("=" * 60)

    test_pairs = ['AED_USD', 'AFN_USD', 'ARS_USD', 'EUR_USD']
    filled_prices_dict = {}
    stats_list = []

    for pair in test_pairs:
        df = load_pair_data_raw(pair)
        if df is not None:
            stats, filled = analyze_missing(df, pair, lookback=30)
            stats_list.append(stats)
            filled_prices_dict[pair] = filled

    print("\n📋 Сводная статистика по заполнению пропусков:")
    stats_df = pd.DataFrame(stats_list)
    print(stats_df.to_string(index=False))
    print(f"\n📦 Словарь filled_prices_dict содержит {len(filled_prices_dict)} пар: {list(filled_prices_dict.keys())}")
    return filled_prices_dict

# ---------- Построение матрицы доступности (шаг 2.4, оптимизированная) ----------
def build_availability_matrix(filled_dict, global_dates):
    """Строит DataFrame доступности (без PerformanceWarning)."""
    global_dates = pd.DatetimeIndex(sorted(global_dates))
    series_list = []
    iterator = filled_dict.items()
    if TQDM_AVAILABLE:
        iterator = tqdm(filled_dict.items(), desc="Построение матрицы доступности")

    for pair, filled_series in iterator:
        mask = filled_series.reindex(global_dates).notna()
        mask.name = pair
        series_list.append(mask)

    availability = pd.concat(series_list, axis=1)
    return availability

def extract_currencies_from_pair(pair):
    """Возвращает множество из двух валют (base, quote)."""
    base, quote = pair.split('_')
    return {base, quote}

def find_t_start(availability_df, pairs_list, core_currencies):
    """
    Находит первую дату, на которую доступны все валюты из core_currencies.
    Возвращает (t_start_date, stats_df).
    """
    pair_currencies = {pair: extract_currencies_from_pair(pair)
                       for pair in pairs_list if pair in availability_df.columns}

    stats = []
    t_start = None

    for date in availability_df.index:
        available_pairs = availability_df.columns[availability_df.loc[date]].tolist()
        available_pairs_count = len(available_pairs)

        currencies_set = set()
        for pair in available_pairs:
            currencies_set.update(pair_currencies.get(pair, set()))

        core_available = core_currencies.issubset(currencies_set)

        stats.append({
            'date': date.date(),
            'available_pairs': available_pairs_count,
            'available_currencies': len(currencies_set),
            'core_available': core_available
        })

        if core_available and t_start is None:
            t_start = date.date()

    stats_df = pd.DataFrame(stats)
    return t_start, stats_df

def load_all_pairs_filled(pairs_list, lookback=30):
    """Загружает все пары, заполняет пропуски, возвращает filled_dict и множество всех дат."""
    filled_dict = {}
    all_dates = set()

    iterator = pairs_list
    if TQDM_AVAILABLE:
        iterator = tqdm(pairs_list, desc="Загрузка и заполнение пар")

    for pair in iterator:
        df = load_pair_data_raw(pair)
        if df is None:
            continue

        series = df.set_index('date')['rate']
        full_idx = pd.date_range(series.index.min(), series.index.max(), freq='D')
        filled = fill_missing_prices(series, full_idx, lookback)

        filled_dict[pair] = filled
        all_dates.update(full_idx)

    return filled_dict, all_dates

def demo_availability_and_tstart():
    """Загружает все пары, строит матрицу доступности, ищет T_start."""
    print("\n" + "=" * 60)
    print(" ШАГ 2.4 – Построение матрицы доступности и поиск T_start")
    print("=" * 60)

    pairs = load_pairs_list()
    print(f"📋 Всего пар для обработки: {len(pairs)}")

    print("\n🔄 Этап 1: загрузка и заполнение всех пар...")
    filled_dict, all_dates_set = load_all_pairs_filled(pairs, lookback=30)
    print(f"   ✅ Загружено и заполнено пар: {len(filled_dict)}")
    print(f"   📅 Уникальных дат во всех рядах: {len(all_dates_set)}")

    print("\n🔄 Этап 2: построение availability_df...")
    availability_df = build_availability_matrix(filled_dict, all_dates_set)
    print(f"   ✅ Размерность: {availability_df.shape[0]} дат × {availability_df.shape[1]} пар")

    print("\n🔄 Этап 3: поиск T_start (первая дата с ядром из 7 валют)...")
    t_start, stats_df = find_t_start(availability_df, pairs, CORE_CURRENCIES)

    if t_start:
        print(f"\n🎯 ** T_start = {t_start} **")
    else:
        print("\n❌ T_start не найден! Ядро валют никогда не было доступно одновременно.")

    # Статистика по годам
    stats_df['year'] = pd.to_datetime(stats_df['date']).dt.year
    yearly_stats = stats_df.groupby('year').agg({
        'available_pairs': 'mean',
        'available_currencies': 'mean',
        'core_available': 'sum'
    }).rename(columns={
        'available_pairs': 'avg_pairs',
        'available_currencies': 'avg_currencies',
        'core_available': 'days_with_core'
    }).round(1)

    print("\n📊 Статистика доступности по годам (первые 10 строк):")
    print(yearly_stats.head(10).to_string())

    core_first_date = stats_df[stats_df['core_available']]['date'].min() if stats_df['core_available'].any() else None
    core_last_date = stats_df[stats_df['core_available']]['date'].max() if stats_df['core_available'].any() else None
    core_days_count = stats_df['core_available'].sum()

    print(f"\n📌 Первая дата с полным ядром: {core_first_date}")
    print(f"📌 Последняя дата с полным ядром: {core_last_date}")
    print(f"📌 Всего дней с полным ядром: {core_days_count}")
    print(f"📌 Процент дней с ядром (от всего периода): {core_days_count/len(stats_df)*100:.1f}%")

    return t_start, availability_df, stats_df

# ---------- ШАГ 2.5a – Формирование списка всех дат для расчёта (без фильтрации) ----------
def get_all_calculation_dates(availability_df, t_start_date):
    """
    Возвращает все даты из availability_df, начиная с t_start_date,
    с ненулевым количеством доступных пар.
    """
    # Обрезаем по T_start
    mask = availability_df.index >= pd.Timestamp(t_start_date)
    dates_idx = availability_df.index[mask]
    
    # Проверяем, что на каждой дате есть хотя бы одна пара
    k_series = availability_df.sum(axis=1)
    k_series = k_series[mask]
    valid_mask = k_series > 0
    valid_dates = dates_idx[valid_mask]
    
    calculation_dates = [d.date() for d in valid_dates]
    
    print("\n" + "=" * 60)
    print(" ШАГ 2.5a – Формирование списка дат для расчёта (без фильтрации)")
    print("=" * 60)
    print(f"\n📅 Всего дат для расчёта (начиная с {t_start_date}): {len(calculation_dates)}")
    print(f"   Первая дата: {calculation_dates[0]}")
    print(f"   Последняя дата: {calculation_dates[-1]}")
    print(f"   Минимальное кол-во пар: {k_series[valid_mask].min()}")
    print(f"   Среднее кол-во пар: {k_series[valid_mask].mean():.1f}")
    print(f"   Максимальное кол-во пар: {k_series[valid_mask].max()}")
    
    # Сохраняем метаданные
    metadata = {
        "t_start": str(t_start_date),
        "total_dates": len(calculation_dates),
        "first_date": str(calculation_dates[0]),
        "last_date": str(calculation_dates[-1]),
        "min_pairs": int(k_series[valid_mask].min()),
        "avg_pairs": float(round(k_series[valid_mask].mean(), 1)),
        "max_pairs": int(k_series[valid_mask].max()),
        "description": "Все даты от T_start до последней доступной даты с наличием хотя бы одной заполненной пары"
    }
    
    metadata_path = METADATA_DIR / "calculation_dates_info.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Метаданные сохранены: {metadata_path}")
    
    return calculation_dates

def demo_calculation_dates(availability_df, t_start):
    """Демонстрация шага 2.5a (обёртка для вызова)."""
    calculation_dates = get_all_calculation_dates(availability_df, t_start)
    print(f"\n✅ Шаг 2.5a завершён. Подготовлено {len(calculation_dates)} дат для расчёта.")
    return calculation_dates

# ---------- Вспомогательные функции (шаг 2.1) ----------
def load_pairs_list():
    """Загружает список валютных пар из JSON."""
    if not PAIRS_JSON.exists():
        raise FileNotFoundError(f"Файл не найден: {PAIRS_JSON}")
    with open(PAIRS_JSON, 'r', encoding='utf-8') as f:
        pairs = json.load(f)
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
    return existing, missing

def get_date_range_from_file(filepath, nrows=1000):
    """Быстро определяет мин и макс дату в CSV."""
    try:
        df = pd.read_csv(filepath, usecols=['datetime'], nrows=nrows)
        df['datetime'] = pd.to_datetime(df['datetime'])
        min_date = df['datetime'].min()
        max_date = df['datetime'].max()
        return min_date, max_date
    except Exception:
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

# ---------- MAIN ----------
def main():
    print("=" * 60)
    print(" ШАГ 2.1 – Адаптация каркаса под реальную структуру данных")
    print("=" * 60)

    pairs = load_pairs_list()
    existing_pairs, missing_pairs = check_files_exist(pairs, DATA_DIR)

    print(f"✅ Загружено пар из JSON: {len(pairs)}")
    print(f"📁 Существующих файлов: {len(existing_pairs)}")
    print(f"❌ Отсутствует файлов: {len(missing_pairs)}")

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

    # Шаг 2.4
    t_start, availability_df, stats_df = demo_availability_and_tstart()
    print(f"\n✅ Шаг 2.4 завершён. T_start = {t_start}")

    # Шаг 2.5a – ВСЕ ДАТЫ (без фильтрации)
    calculation_dates = demo_calculation_dates(availability_df, t_start)

    print("\n" + "=" * 60)
    print(" ПОДГОТОВКА ДАННЫХ ЗАВЕРШЕНА")
    print("=" * 60)
    print(f"\n🎯 Стартовая дата расчёта (T_start): {t_start}")
    print(f"📅 Всего дат для расчёта: {len(calculation_dates)}")
    print(f"🔄 Следующий шаг: 2.6 – Интеграция ядра расчёта МНК")
    
if __name__ == "__main__":
    main()
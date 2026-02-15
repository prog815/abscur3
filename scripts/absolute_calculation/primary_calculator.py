#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
primary_calculator.py – Первичный расчёт абсолютных курсов AbsCur3
Версия с шагом 2.7: сохранение результатов и метаданных.
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np
from collections import defaultdict
import datetime
import csv

# ---------- tqdm для прогресс-баров ----------
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("⚠️  tqdm не установлен. Рекомендуется: pip install tqdm")

# ---------- Конфигурация ----------
PAIRS_JSON = Path("data/metadata/currency_pairs.json")
DATA_DIR = Path("data/raw/twelve_data/pairs")
CORE_CURRENCIES = {'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD'}
METADATA_DIR = Path("data/absolute/metadata")
METADATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------- КРИТИЧЕСКИЕ ПАРЫ (из отчёта Kaggle, 18 штук) ----------
CRITICAL_PAIRS = {
    'SHP_USD', 'USD_BTN', 'SYP_USD', 'VND_USD', 'IDR_EUR', 'IDR_GBP',
    'USD_AWG', 'USD_GYD', 'USD_PAB', 'BMD_USD', 'AED_USD', 'USD_AED',
    'BOB_USD', 'AFN_USD', 'ARS_USD', 'BRL_USD', 'AZN_RUB', 'BGN_RUB'
}

# ---------- РЕЖИМ ТЕСТИРОВАНИЯ ----------
# True  – обработать только первые 100 и последние 100 дат (для отладки)
# False – обработать все 16850 дат (полный расчёт)
TEST_MODE = False   # после успешного теста переключите на False для полного расчёта
TEST_DATES_LIMIT = 100

# ---------- Параметры сохранения ----------
OUTLIER_THRESHOLD = 10.0   # порог для выбросов (в процентах)

# ---------- Кеш для загруженных данных ----------
_DATA_CACHE = {}

# ========== ШАГИ 2.1–2.3 (без изменений) ==========
def convert_to_filename(pair):
    return pair.replace("_", "") + ".csv"

def load_pair_data_raw(pair_name, use_cache=True, force_reload=False):
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

def fill_missing_prices(series, full_date_index, lookback_days=30):
    filled = series.reindex(full_date_index)
    filled = filled.ffill(limit=lookback_days)
    return filled

def analyze_missing(original_df, pair_name, lookback=30):
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

# ========== ШАГ 2.4 – Построение матрицы доступности и поиск T_start ==========
def build_availability_matrix(filled_dict, global_dates):
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
    base, quote = pair.split('_')
    return {base, quote}

def find_t_start(availability_df, pairs_list, core_currencies):
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
    """Загружает все пары, строит матрицу доступности, ищет T_start.
       Возвращает: t_start, availability_df, stats_df, filled_dict"""
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
    return t_start, availability_df, stats_df, filled_dict

# ========== ШАГ 2.5a – Формирование списка дат для расчёта ==========
def get_all_calculation_dates(availability_df, t_start_date):
    mask = availability_df.index >= pd.Timestamp(t_start_date)
    dates_idx = availability_df.index[mask]
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
    calculation_dates = get_all_calculation_dates(availability_df, t_start)
    print(f"\n✅ Шаг 2.5a завершён. Подготовлено {len(calculation_dates)} дат для расчёта.")
    return calculation_dates

# ========== ШАГ 2.6 – ЯДРО РАСЧЁТА МНК ==========
def calculate_absolute_rates_for_date(
    date,
    availability_df,
    filled_dict,
    critical_pairs,
    exclude_critical=True,
    verbose=False
):
    """
    Вычисляет абсолютные курсы для одной даты.
    Возвращает словарь с результатами или None.
    """
    date_ts = pd.Timestamp(date)
    if date_ts not in availability_df.index:
        return None
    available_pairs = availability_df.columns[availability_df.loc[date_ts]].tolist()
    
    if exclude_critical:
        filtered_pairs = [p for p in available_pairs if p not in critical_pairs]
    else:
        filtered_pairs = available_pairs.copy()
    
    if len(filtered_pairs) == 0:
        return None
    
    currencies_set = set()
    pair_currencies = {}
    for pair in filtered_pairs:
        base, quote = pair.split('_')
        currencies_set.add(base)
        currencies_set.add(quote)
        pair_currencies[pair] = (base, quote)
    
    n_currencies = len(currencies_set)
    if n_currencies < 5:
        return None
    
    currency_to_idx = {c: i for i, c in enumerate(sorted(currencies_set))}
    n = len(currency_to_idx)
    m = len(filtered_pairs)
    
    M = np.zeros((m, n))
    p = np.zeros(m)
    
    for i, pair in enumerate(filtered_pairs):
        base, quote = pair_currencies[pair]
        base_idx = currency_to_idx[base]
        quote_idx = currency_to_idx[quote]
        M[i, base_idx] = 1
        M[i, quote_idx] = -1
        
        try:
            rate = filled_dict[pair].loc[date_ts]
        except (KeyError, IndexError):
            continue
        p[i] = np.log(rate)
    
    try:
        a, residuals, rank, s = np.linalg.lstsq(M, p, rcond=None)
    except np.linalg.LinAlgError:
        return None
    
    a -= np.mean(a)
    absolute_rates = {currency: np.exp(a[idx]) for currency, idx in currency_to_idx.items()}
    
    errors = {}
    for pair in filtered_pairs:
        base, quote = pair_currencies[pair]
        a_base = a[currency_to_idx[base]]
        a_quote = a[currency_to_idx[quote]]
        p_calc = np.exp(a_base - a_quote)
        try:
            rate_actual = filled_dict[pair].loc[date_ts]
        except:
            continue
        error = (rate_actual - p_calc) / rate_actual * 100
        errors[pair] = error
    
    return {
        'date': date,
        'absolute_rates': absolute_rates,
        'errors': errors,
        'n_currencies': n_currencies,
        'n_pairs': m,
        'success': True
    }

def demo_calculation_loop(
    calculation_dates,
    availability_df,
    filled_dict,
    critical_pairs,
    exclude_critical=True,
    test_mode=True,
    test_limit=100
):
    print("\n" + "=" * 60)
    print(" ШАГ 2.6 – Интеграция ядра расчёта МНК")
    print("=" * 60)
    
    if exclude_critical:
        print(f"🔍 Исключаем критические пары: {len(critical_pairs)} шт.")
    else:
        print("🔍 Используем все доступные пары (без фильтрации)")
    
    if test_mode and len(calculation_dates) > 2 * test_limit:
        dates_to_process = calculation_dates[:test_limit] + calculation_dates[-test_limit:]
        print(f"\n🧪 ТЕСТОВЫЙ РЕЖИМ: обрабатываем {len(dates_to_process)} дат")
        print(f"   (первые {test_limit} и последние {test_limit} из {len(calculation_dates)})")
    else:
        dates_to_process = calculation_dates
        print(f"\n📅 Полный расчёт: {len(dates_to_process)} дат")
    
    results = []
    failed_dates = []
    all_errors = []
    
    iterator = dates_to_process
    if TQDM_AVAILABLE:
        iterator = tqdm(dates_to_process, desc="Расчёт абсолютных курсов")
    
    for date in iterator:
        res = calculate_absolute_rates_for_date(
            date,
            availability_df,
            filled_dict,
            critical_pairs,
            exclude_critical=exclude_critical,
            verbose=False
        )
        if res is None:
            failed_dates.append(date)
        else:
            results.append(res)
            all_errors.extend(res['errors'].values())
    
    print(f"\n📊 Статистика расчёта:")
    print(f"   ✅ Успешно обработано дат: {len(results)}")
    print(f"   ❌ Пропущено дат: {len(failed_dates)}")
    
    if all_errors:
        all_errors = np.array(all_errors)
        print(f"\n📈 Погрешности (ε, %):")
        print(f"   Среднее: {np.mean(all_errors):.6f}%")
        print(f"   Медиана: {np.median(all_errors):.6f}%")
        print(f"   Std:     {np.std(all_errors):.6f}%")
        print(f"   Мин:     {np.min(all_errors):.6f}%")
        print(f"   Макс:    {np.max(all_errors):.6f}%")
        q = np.percentile(all_errors, [25, 50, 75, 95, 99])
        print(f"   25%:     {q[0]:.6f}%")
        print(f"   50%:     {q[1]:.6f}%")
        print(f"   75%:     {q[2]:.6f}%")
        print(f"   95%:     {q[3]:.6f}%")
        print(f"   99%:     {q[4]:.6f}%")
    
    # Статистика по количеству валют и пар
    n_currencies_list = [r['n_currencies'] for r in results]
    n_pairs_list = [r['n_pairs'] for r in results]
    if n_currencies_list:
        print(f"\n💰 Количество валют на дату:")
        print(f"   Среднее: {np.mean(n_currencies_list):.1f}")
        print(f"   Мин:     {np.min(n_currencies_list)}")
        print(f"   Макс:    {np.max(n_currencies_list)}")
    if n_pairs_list:
        print(f"\n🔗 Количество пар на дату:")
        print(f"   Среднее: {np.mean(n_pairs_list):.1f}")
        print(f"   Мин:     {np.min(n_pairs_list)}")
        print(f"   Макс:    {np.max(n_pairs_list)}")
    
    # Сохраняем сводку
    summary = {
        'test_mode': test_mode,
        'dates_processed': len(results),
        'dates_failed': len(failed_dates),
        'mean_error': float(np.mean(all_errors)) if len(all_errors) > 0 else None,
        'median_error': float(np.median(all_errors)) if len(all_errors) > 0 else None,
        'max_error': float(np.max(all_errors)) if len(all_errors) > 0 else None,
        'mean_currencies': float(np.mean(n_currencies_list)) if n_currencies_list else None,
        'mean_pairs': float(np.mean(n_pairs_list)) if n_pairs_list else None,
    }
    summary_path = METADATA_DIR / "calculation_summary_step26.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\n💾 Сводка сохранена: {summary_path}")
    
    return results, failed_dates

# ========== ШАГ 2.7 – Сохранение результатов и метаданных ==========
def save_results_step27(results, failed_dates, t_start, critical_pairs, outlier_threshold=10.0):
    """Сохраняет все результаты в структуру каталогов, генерирует метаданные."""
    
    # Создаём директории
    DAILY_DIR = Path("data/absolute/daily")
    CURRENCIES_DIR = Path("data/absolute/currencies")
    ERRORS_DIR = Path("data/absolute/errors")
    METADATA_DIR = Path("data/absolute/metadata")
    
    for d in [DAILY_DIR, CURRENCIES_DIR, ERRORS_DIR, METADATA_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    
    # Накопители
    currency_accumulator = defaultdict(list)   # {currency: [(date, value), ...]}
    outliers = []                               # список выбросов
    pair_stats = defaultdict(lambda: {'count': 0, 'sum_abs_error': 0.0})
    all_errors = []                              # для общей статистики
    
    print("\n" + "="*60)
    print(" ШАГ 2.7 – Сохранение результатов и метаданных")
    print("="*60)
    
    iterator = results
    if TQDM_AVAILABLE:
        iterator = tqdm(results, desc="Сохранение результатов")
    
    for res in iterator:
        date = res['date']
        abs_rates = res['absolute_rates']
        errors = res['errors']
        
        # 1. Daily файл
        daily_file = DAILY_DIR / f"{date.isoformat()}.csv"
        with open(daily_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['currency', 'absolute_value'])
            for currency, value in sorted(abs_rates.items()):
                writer.writerow([currency, value])
        
        # 2. Накопление для валют
        for currency, value in abs_rates.items():
            currency_accumulator[currency].append((date, value))
        
        # 3. Errors файл
        errors_file = ERRORS_DIR / f"{date.isoformat()}.csv"
        with open(errors_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['pair', 'error_percent'])
            for pair, err in sorted(errors.items()):
                writer.writerow([pair, err])
                # Обновляем статистику по парам
                pair_stats[pair]['count'] += 1
                pair_stats[pair]['sum_abs_error'] += abs(err)
                all_errors.append(err)
                # Проверка на выброс
                if abs(err) > outlier_threshold:
                    outliers.append({
                        'date': date.isoformat(),
                        'pair': pair,
                        'error': err
                    })
    
    # Сохраняем файлы по валютам
    print("\n📈 Сохранение файлов по валютам...")
    curr_iterator = currency_accumulator.items()
    if TQDM_AVAILABLE:
        curr_iterator = tqdm(currency_accumulator.items(), desc="Валюты")
    
    for currency, records in curr_iterator:
        records.sort(key=lambda x: x[0])  # по дате
        curr_file = CURRENCIES_DIR / f"{currency}.csv"
        with open(curr_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['date', 'absolute_value'])
            for date, value in records:
                writer.writerow([date.isoformat(), value])
    
    # ---- Метаданные ----
    
    # 1. Общий отчёт
    all_errors_arr = np.array(all_errors)
    report = {
        'calculation_date': datetime.datetime.now().isoformat(),
        't_start': str(t_start),
        'total_dates_processed': len(results),
        'total_dates_failed': len(failed_dates),
        'total_pairs_used': len(pair_stats),
        'outlier_threshold': outlier_threshold,
        'critical_pairs_excluded': list(critical_pairs),
        'error_stats': {
            'mean': float(np.mean(all_errors_arr)),
            'median': float(np.median(all_errors_arr)),
            'std': float(np.std(all_errors_arr)),
            'min': float(np.min(all_errors_arr)),
            'max': float(np.max(all_errors_arr)),
            'percentiles': {
                '25': float(np.percentile(all_errors_arr, 25)),
                '50': float(np.percentile(all_errors_arr, 50)),
                '75': float(np.percentile(all_errors_arr, 75)),
                '95': float(np.percentile(all_errors_arr, 95)),
                '99': float(np.percentile(all_errors_arr, 99))
            }
        }
    }
    
    report_file = METADATA_DIR / "primary_calculation_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"💾 Отчёт сохранён: {report_file}")
    
    # 2. Выбросы
    outliers_file = METADATA_DIR / "outliers.json"
    with open(outliers_file, 'w', encoding='utf-8') as f:
        json.dump(outliers, f, indent=2, ensure_ascii=False)
    print(f"💾 Выбросы сохранены: {outliers_file} (всего {len(outliers)})")
    
    # 3. Статистика по парам (топ по средней абсолютной ошибке)
    pair_stats_list = []
    for pair, st in pair_stats.items():
        avg_abs_error = st['sum_abs_error'] / st['count']
        pair_stats_list.append({
            'pair': pair,
            'count': st['count'],
            'avg_abs_error': avg_abs_error
        })
    pair_stats_list.sort(key=lambda x: x['avg_abs_error'], reverse=True)
    
    pair_stats_file = METADATA_DIR / "pair_error_stats.json"
    with open(pair_stats_file, 'w', encoding='utf-8') as f:
        json.dump(pair_stats_list[:100], f, indent=2)  # топ-100
    print(f"💾 Статистика по парам (топ-100) сохранена: {pair_stats_file}")
    
    print("\n✅ Шаг 2.7 завершён. Все результаты сохранены.")
    
    return report

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def load_pairs_list():
    if not PAIRS_JSON.exists():
        raise FileNotFoundError(f"Файл не найден: {PAIRS_JSON}")
    with open(PAIRS_JSON, 'r', encoding='utf-8') as f:
        pairs = json.load(f)
    return pairs

def check_files_exist(pairs, data_dir):
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
    try:
        df = pd.read_csv(filepath, usecols=['datetime'], nrows=nrows)
        df['datetime'] = pd.to_datetime(df['datetime'])
        min_date = df['datetime'].min()
        max_date = df['datetime'].max()
        return min_date, max_date
    except Exception:
        return None, None

def demo_load_pair_data():
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

# ========== MAIN ==========
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
    t_start, availability_df, stats_df, filled_dict = demo_availability_and_tstart()
    print(f"\n✅ Шаг 2.4 завершён. T_start = {t_start}")

    # Шаг 2.5a
    calculation_dates = demo_calculation_dates(availability_df, t_start)

    # Шаг 2.6 – основной цикл расчёта
    results, failed_dates = demo_calculation_loop(
        calculation_dates,
        availability_df,
        filled_dict,
        critical_pairs=CRITICAL_PAIRS,
        exclude_critical=True,
        test_mode=TEST_MODE,
        test_limit=TEST_DATES_LIMIT
    )

    # Шаг 2.7 – сохранение результатов
    save_results_step27(results, failed_dates, t_start, CRITICAL_PAIRS, outlier_threshold=OUTLIER_THRESHOLD)

    print("\n" + "=" * 60)
    print(" ПЕРВИЧНЫЙ РАСЧЁТ ЗАВЕРШЁН")
    print("=" * 60)
    print(f"\n🎯 Стартовая дата расчёта (T_start): {t_start}")
    print(f"📅 Всего дат для расчёта: {len(calculation_dates)}")
    print(f"✅ Успешно обработано дат: {len(results)}")
    print(f"📁 Результаты сохранены в data/absolute/")
    print(f"📊 Отчёт: data/absolute/metadata/primary_calculation_report.json")

if __name__ == "__main__":
    main()
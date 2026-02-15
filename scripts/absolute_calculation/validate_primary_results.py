#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_primary_results.py – Шаг 2.8: Валидация результатов первичного расчёта.
Проверяет:
- Исключение критических пар
- Погрешности для основных пар (<0.01%)
- Анализ выбросов
- Сравнение с выводами Kaggle Notebook
- Формирование отчёта validation_report.json
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import datetime

# ---------- Конфигурация ----------
METADATA_DIR = Path("data/absolute/metadata")
ERRORS_DIR = Path("data/absolute/errors")
REPORT_FILE = METADATA_DIR / "primary_calculation_report.json"
OUTLIERS_FILE = METADATA_DIR / "outliers.json"
VALIDATION_REPORT_FILE = METADATA_DIR / "validation_report.json"

# Основные пары для проверки (AC5)
MAJOR_PAIRS = ['EUR_USD', 'USD_JPY', 'GBP_USD', 'AUD_USD', 'USD_CHF', 'USD_CAD']

# Критические пары из отчёта Kaggle (должны быть исключены)
CRITICAL_PAIRS = {
    'SHP_USD', 'USD_BTN', 'SYP_USD', 'VND_USD', 'IDR_EUR', 'IDR_GBP',
    'USD_AWG', 'USD_GYD', 'USD_PAB', 'BMD_USD', 'AED_USD', 'USD_AED',
    'BOB_USD', 'AFN_USD', 'ARS_USD', 'BRL_USD', 'AZN_RUB', 'BGN_RUB'
}

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_error_files():
    """Возвращает список всех файлов errors (отсортированных)."""
    return sorted(ERRORS_DIR.glob("*.csv"))

def collect_errors_for_pairs(pairs):
    """
    Проходит по всем errors файлам и собирает ошибки для указанных пар.
    Возвращает dict: {pair: list_of_errors}
    """
    error_files = get_error_files()
    print(f"📂 Найдено {len(error_files)} файлов errors. Сбор данных для {len(pairs)} пар...")
    
    pair_errors = {pair: [] for pair in pairs}
    
    for file in error_files:
        try:
            df = pd.read_csv(file)
        except Exception as e:
            print(f"⚠️ Ошибка чтения {file}: {e}")
            continue
        
        for pair in pairs:
            if pair in df['pair'].values:
                err = df.loc[df['pair'] == pair, 'error_percent'].iloc[0]
                pair_errors[pair].append(err)
    
    return pair_errors

def analyze_outliers(outliers_data):
    """Анализирует выбросы: распределение по годам и по парам."""
    if not outliers_data:
        return {}
    
    dates = [item['date'] for item in outliers_data]
    years = [d[:4] for d in dates]
    year_counts = Counter(years)
    
    pairs = [item['pair'] for item in outliers_data]
    pair_counts = Counter(pairs)
    
    return {
        'total_outliers': len(outliers_data),
        'outliers_by_year': dict(sorted(year_counts.items())),
        'top10_outlier_pairs': pair_counts.most_common(10)
    }

def check_critical_pairs_excluded(pair_errors):
    """Проверяет, что критические пары отсутствуют в собранных ошибках."""
    found = [p for p in CRITICAL_PAIRS if p in pair_errors and pair_errors[p]]
    return {
        'critical_pairs_excluded': len(found) == 0,
        'found_in_errors': found
    }

def check_major_pairs_accuracy(pair_errors, threshold=0.01):
    """Проверяет, что средняя абсолютная ошибка для основных пар < threshold."""
    results = {}
    all_ok = True
    for pair in MAJOR_PAIRS:
        errors = np.array(pair_errors.get(pair, []))
        if len(errors) == 0:
            results[pair] = {'status': 'NO_DATA', 'mean_abs': None}
            all_ok = False
            continue
        mean_abs = np.mean(np.abs(errors))
        median = np.median(errors)
        max_err = np.max(np.abs(errors))
        ok = mean_abs < threshold
        results[pair] = {
            'status': 'OK' if ok else 'FAIL',
            'count': len(errors),
            'mean_abs_error': float(mean_abs),
            'median_error': float(median),
            'max_abs_error': float(max_err),
            'threshold': threshold
        }
        if not ok:
            all_ok = False
    return all_ok, results

def generate_validation_report():
    """Основная функция валидации."""
    print("="*60)
    print(" ШАГ 2.8 – Валидация результатов первичного расчёта")
    print("="*60)
    
    # 1. Загружаем общий отчёт
    if REPORT_FILE.exists():
        report = load_json(REPORT_FILE)
        print(f"✅ Загружен отчёт: {REPORT_FILE}")
        print(f"   Всего дат: {report['total_dates_processed']}")
        print(f"   Всего пар использовано: {report['total_pairs_used']}")
        print(f"   Медианная погрешность: {report['error_stats']['median']:.6f}%")
    else:
        print(f"❌ Файл {REPORT_FILE} не найден.")
        report = {}
    
    # 2. Загружаем выбросы
    if OUTLIERS_FILE.exists():
        outliers = load_json(OUTLIERS_FILE)
        outlier_stats = analyze_outliers(outliers)
        print(f"\n📊 Анализ выбросов (|ε| > 10%):")
        print(f"   Всего выбросов: {outlier_stats['total_outliers']}")
        print(f"   Топ-5 лет по выбросам: {dict(list(outlier_stats['outliers_by_year'].items())[:5])}")
        print(f"   Топ-5 пар по выбросам: {outlier_stats['top10_outlier_pairs'][:5]}")
    else:
        print(f"⚠️ Файл {OUTLIERS_FILE} не найден.")
        outlier_stats = {}
    
    # 3. Собираем ошибки для основных пар
    print("\n🔄 Сбор погрешностей для основных пар...")
    pair_errors = collect_errors_for_pairs(MAJOR_PAIRS + list(CRITICAL_PAIRS))
    
    # 4. Проверка исключения критических пар
    crit_check = check_critical_pairs_excluded(pair_errors)
    print(f"\n🔍 Проверка критических пар:")
    if crit_check['critical_pairs_excluded']:
        print("   ✅ Все критические пары исключены из результатов.")
    else:
        print(f"   ❌ Найдены критические пары в ошибках: {crit_check['found_in_errors']}")
    
    # 5. Проверка точности основных пар
    print(f"\n📈 Проверка точности для основных пар (требование <0.01%):")
    all_ok, major_results = check_major_pairs_accuracy(pair_errors, threshold=0.01)
    for pair, res in major_results.items():
        if res['status'] == 'NO_DATA':
            print(f"   ⚠️ {pair}: нет данных")
        elif res['status'] == 'OK':
            print(f"   ✅ {pair}: средняя |ε| = {res['mean_abs_error']:.6f}% (OK)")
        else:
            print(f"   ❌ {pair}: средняя |ε| = {res['mean_abs_error']:.6f}% > порога")
    
    # 6. Дополнительный анализ: распределение погрешностей по годам (на основе выбросов)
    # Можно также добавить проверку стабильности для ранних и поздних дат
    # Но для этого нужны данные по всем датам, что сложно. Используем выбросы как индикатор.
    
    # 7. Формируем итоговый отчёт
    validation_report = {
        'timestamp': datetime.datetime.now().isoformat(),
        'primary_report_summary': {
            'total_dates': report.get('total_dates_processed'),
            'median_error': report.get('error_stats', {}).get('median')
        },
        'outlier_analysis': outlier_stats,
        'critical_pairs_check': crit_check,
        'major_pairs_accuracy': major_results,
        'overall_status': 'PASS' if (all_ok and crit_check['critical_pairs_excluded']) else 'FAIL'
    }
    
    # Сохраняем отчёт
    with open(VALIDATION_REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(validation_report, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Отчёт валидации сохранён: {VALIDATION_REPORT_FILE}")
    
    # Итоговый вердикт
    print("\n" + "="*60)
    print(" ИТОГОВЫЙ ВЕРДИКТ")
    print("="*60)
    if validation_report['overall_status'] == 'PASS':
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ. Результаты пригодны для использования.")
    else:
        print("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ. Проверьте отчёт для деталей.")
    
    return validation_report

if __name__ == "__main__":
    generate_validation_report()
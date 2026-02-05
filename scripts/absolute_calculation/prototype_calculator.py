#!/usr/bin/env python3
"""
Прототип алгоритма расчета абсолютных валютных курсов методом наименьших квадратов
Запуск из корневого каталога: python scripts/absolute_calculation/prototype_calculator.py
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path

# Добавляем корневую директорию в путь для импорта модулей
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from scripts.absolute_calculation.test_data import TEST_PAIRS, TEST_DATE_RANGE
from scripts.absolute_calculation.utils import (
    load_pair_data,
    build_incidence_matrix,
    solve_least_squares,
    calculate_errors,
    save_daily_results,
    save_error_results
)


def load_test_data_for_date(date_str):
    """
    Загружает данные для тестовых пар на указанную дату
    
    Args:
        date_str (str): Дата в формате 'YYYY-MM-DD'
        
    Returns:
        dict: Словарь с данными пар {pair: close_price}
    """
    date_data = {}
    
    for pair in TEST_PAIRS:
        try:
            # Загружаем данные для пары
            df = load_pair_data(pair)
            if df is not None and date_str in df.index:
                close_price = df.loc[date_str, 'close']
                if pd.notna(close_price):
                    date_data[pair] = close_price
        except Exception as e:
            print(f"Ошибка при загрузке данных для пары {pair}: {e}")
    
    return date_data


def process_date(date_str):
    """
    Обрабатывает одну дату: строит матрицу, решает СЛАУ, вычисляет погрешности
    
    Args:
        date_str (str): Дата в формате 'YYYY-MM-DD'
        
    Returns:
        tuple: (результаты_абсолютных_курсов, результаты_погрешностей) или (None, None) при ошибке
    """
    print(f"Обработка даты: {date_str}")
    
    # Загружаем данные для даты
    date_data = load_test_data_for_date(date_str)
    
    if len(date_data) < 2:  # Нужно хотя бы 2 пары для построения системы
        print(f"  Недостаточно данных: {len(date_data)} пар")
        return None, None
    
    # Получаем уникальные валюты
    currencies = set()
    for pair in date_data.keys():
        cur1, cur2 = pair[:3], pair[3:]
        currencies.add(cur1)
        currencies.add(cur2)
    
    if len(currencies) < 5:  # Проверяем условие n >= 5
        print(f"  Недостаточно уникальных валют: {len(currencies)} (требуется >= 5)")
        return None, None
    
    # Строим матрицу инцидентности
    M, currency_list, pair_list = build_incidence_matrix(date_data)
    
    if M is None or len(pair_list) == 0:
        return None, None
    
    # Формируем вектор p (логарифмы курсов)
    p = np.array([np.log(date_data[pair]) for pair in pair_list])
    
    # Решаем методом наименьших квадратов
    a = solve_least_squares(M, p)
    
    if a is None:
        return None, None
    
    # Вычисляем абсолютные курсы (экспонента от логарифмов)
    absolute_rates = {currency: np.exp(val) for currency, val in zip(currency_list, a)}
    
    # Вычисляем погрешности
    errors = calculate_errors(date_data, absolute_rates, pair_list)
    
    return absolute_rates, errors


def run_prototype():
    """
    Основная функция запуска прототипа
    """
    print("=" * 60)
    print("Запуск прототипа расчета абсолютных валютных курсов")
    print("=" * 60)
    
    # Создаем директории для результатов
    results_dir = root_dir / "data" / "absolute" / "prototype"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Генерируем список дат для тестирования
    start_date = datetime.strptime(TEST_DATE_RANGE['start'], '%Y-%m-%d')
    end_date = datetime.strptime(TEST_DATE_RANGE['end'], '%Y-%m-%d')
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    all_results = {}
    all_errors = {}
    processed_dates = 0
    skipped_dates = 0
    
    print(f"\nТестовый период: {TEST_DATE_RANGE['start']} - {TEST_DATE_RANGE['end']}")
    print(f"Тестовые пары ({len(TEST_PAIRS)}): {', '.join(TEST_PAIRS)}")
    print(f"Количество дней для обработки: {len(date_range)}\n")
    
    # Обрабатываем каждую дату
    for date in date_range:
        date_str = date.strftime('%Y-%m-%d')
        
        absolute_rates, errors = process_date(date_str)
        
        if absolute_rates is not None and errors is not None:
            all_results[date_str] = absolute_rates
            all_errors[date_str] = errors
            processed_dates += 1
            
            # Выводим краткую статистику для даты
            if errors:
                avg_error = np.mean([abs(e['error_percent']) for e in errors.values()])
                max_error = np.max([abs(e['error_percent']) for e in errors.values()])
                print(f"  ✓ {date_str}: {len(absolute_rates)} валют, {len(errors)} пар, сред. погр.: {avg_error:.4f}%, макс.: {max_error:.4f}%")
        else:
            skipped_dates += 1
    
    # Сохраняем результаты
    if all_results:
        print(f"\nСохранение результатов...")
        
        # Сохраняем ежедневные результаты
        for date_str, rates in all_results.items():
            save_daily_results(date_str, rates, results_dir / "results")
        
        # Сохраняем погрешности
        for date_str, errors in all_errors.items():
            save_error_results(date_str, errors, results_dir / "errors")
        
        # Сохраняем метаданные
        metadata = {
            "processed_dates": processed_dates,
            "skipped_dates": skipped_dates,
            "test_pairs": TEST_PAIRS,
            "date_range": TEST_DATE_RANGE,
            "total_currencies_found": len(set().union(*[r.keys() for r in all_results.values()])),
            "run_timestamp": datetime.now().isoformat()
        }
        
        metadata_file = results_dir / "metadata" / "run_metadata.json"
        metadata_file.parent.mkdir(exist_ok=True)
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Результаты сохранены в: {results_dir}")
        print(f"  Обработано дат: {processed_dates}")
        print(f"  Пропущено дат: {skipped_dates}")
        
        # Выводим сводную статистику по погрешностям
        if all_errors:
            all_error_values = []
            for date_errors in all_errors.values():
                for error_data in date_errors.values():
                    all_error_values.append(abs(error_data['error_percent']))
            
            if all_error_values:
                print(f"  Средняя абсолютная погрешность: {np.mean(all_error_values):.6f}%")
                print(f"  Максимальная абсолютная погрешность: {np.max(all_error_values):.6f}%")
                print(f"  Медианная абсолютная погрешность: {np.median(all_error_values):.6f}%")
    
    else:
        print("\n✗ Не удалось обработать ни одной даты. Проверьте наличие данных.")
    
    print("\n" + "=" * 60)
    print("Прототип завершен")
    print("=" * 60)


if __name__ == "__main__":
    run_prototype()
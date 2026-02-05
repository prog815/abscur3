#!/usr/bin/env python3
"""
Шаг 4: Расчет погрешностей для одной даты
Запуск из корневого каталога: python scripts/absolute_calculation/step4_calculate_errors.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Добавляем путь к корневому каталогу для импорта функций из шага 3
sys.path.insert(0, str(Path(__file__).parent))

def load_pair_data(pair_name):
    """Загружает данные для одной валютной пары"""
    try:
        root_dir = Path(__file__).parent.parent.parent
        file_path = root_dir / "data" / "raw" / "twelve_data" / "pairs" / f"{pair_name}.csv"
        
        if not file_path.exists():
            print(f"  ✗ Файл не найден: {pair_name}.csv")
            return None
        
        df = pd.read_csv(file_path)
        
        if 'datetime' in df.columns:
            df = df.rename(columns={'datetime': 'timestamp'})
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        
        return df
    
    except Exception as e:
        print(f"  ✗ Ошибка при загрузке {pair_name}: {e}")
        return None

def solve_for_date(date_str, pairs):
    """Решает систему для указанной даты и пар"""
    # Загружаем данные
    pairs_data = {}
    for pair in pairs:
        df = load_pair_data(pair)
        if df is not None:
            pairs_data[pair] = df
    
    # Проверяем наличие данных на указанную дату
    date_dt = pd.to_datetime(date_str)
    date_data = {}
    
    for pair, df in pairs_data.items():
        if date_dt in df.index:
            close_price = df.loc[date_dt, 'close']
            if pd.notna(close_price):
                date_data[pair] = close_price
    
    if len(date_data) < 2:
        print(f"  ✗ Недостаточно данных на дату {date_str}")
        return None, None, None, None, None
    
    # Строим матрицу
    currencies = set()
    for pair in date_data.keys():
        cur1, cur2 = pair[:3], pair[3:]
        currencies.add(cur1)
        currencies.add(cur2)
    
    currency_list = sorted(list(currencies))
    pair_list = sorted(list(date_data.keys()))
    
    # Создаем матрицу M
    currency_to_idx = {curr: i for i, curr in enumerate(currency_list)}
    m = len(pair_list)
    n = len(currency_list)
    M = np.zeros((m, n))
    
    for i, pair in enumerate(pair_list):
        cur1, cur2 = pair[:3], pair[3:]
        if cur1 in currency_to_idx:
            M[i, currency_to_idx[cur1]] = 1
        if cur2 in currency_to_idx:
            M[i, currency_to_idx[cur2]] = -1
    
    # Создаем вектор p
    p = np.array([np.log(date_data[pair]) for pair in pair_list])
    
    # Решаем систему
    try:
        a, residuals, rank, s = np.linalg.lstsq(M, p, rcond=None)
        a = a - np.mean(a)  # Нормализуем
        
        # Вычисляем абсолютные курсы
        absolute_rates = {currency: np.exp(a[i]) for i, currency in enumerate(currency_list)}
        
        # Нормализуем (USD = 1)
        if 'USD' in absolute_rates:
            usd_rate = absolute_rates['USD']
            for currency in absolute_rates:
                absolute_rates[currency] = absolute_rates[currency] / usd_rate
        
        return absolute_rates, date_data, pair_list, currency_list, a
    
    except Exception as e:
        print(f"  ✗ Ошибка при решении системы: {e}")
        return None, None, None, None, None

def calculate_detailed_errors(absolute_rates, actual_rates, pair_list):
    """Вычисляет детальные погрешности для всех пар"""
    errors = []
    
    for pair in pair_list:
        cur1, cur2 = pair[:3], pair[3:]
        
        if cur1 not in absolute_rates or cur2 not in absolute_rates:
            continue
        
        actual = actual_rates[pair]
        calculated = absolute_rates[cur1] / absolute_rates[cur2]
        
        error_abs = actual - calculated
        error_percent = (error_abs / actual) * 100
        
        errors.append({
            'pair': pair,
            'actual': actual,
            'calculated': calculated,
            'error_absolute': error_abs,
            'error_percent': error_percent,
            'abs_error_percent': abs(error_percent)
        })
    
    return errors

def print_error_table(errors):
    """Выводит красивую таблицу с погрешностями"""
    print("\n" + "=" * 80)
    print("ТАБЛИЦА ПОГРЕШНОСТЕЙ РАСЧЕТА")
    print("=" * 80)
    print(f"{'Пара':<10} {'Фактический':>15} {'Рассчитанный':>15} {'Абс. ошибка':>15} {'Отн. ошибка, %':>15}")
    print("-" * 80)
    
    for error in errors:
        print(f"{error['pair']:<10} "
              f"{error['actual']:>15.6f} "
              f"{error['calculated']:>15.6f} "
              f"{error['error_absolute']:>15.6f} "
              f"{error['error_percent']:>15.6f}")
    
    print("-" * 80)
    
    # Выводим статистику
    if errors:
        abs_errors = [e['abs_error_percent'] for e in errors]
        avg_error = np.mean(abs_errors)
        max_error = np.max(abs_errors)
        min_error = np.min(abs_errors)
        
        print(f"\nСТАТИСТИКА:")
        print(f"  Средняя абсолютная погрешность: {avg_error:.6f}%")
        print(f"  Максимальная погрешность:        {max_error:.6f}%")
        print(f"  Минимальная погрешность:         {min_error:.6f}%")
        print(f"  Количество пар:                  {len(errors)}")
        
        # Оценка качества
        if avg_error < 0.01:
            quality = "ОТЛИЧНО"
        elif avg_error < 0.1:
            quality = "ХОРОШО"
        elif avg_error < 1:
            quality = "УДОВЛЕТВОРИТЕЛЬНО"
        else:
            quality = "ПЛОХО"
        
        print(f"\n  ОЦЕНКА КАЧЕСТВА: {quality}")

def save_results_to_files(date_str, absolute_rates, errors):
    """Сохраняет результаты в CSV файлы"""
    # Создаем директорию для результатов
    results_dir = Path(__file__).parent.parent.parent / "data" / "absolute" / "step4_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Сохраняем абсолютные курсы
    abs_file = results_dir / f"absolute_rates_{date_str}.csv"
    abs_df = pd.DataFrame.from_dict(absolute_rates, orient='index', columns=['absolute_value'])
    abs_df.index.name = 'currency'
    abs_df.to_csv(abs_file)
    print(f"\n✓ Абсолютные курсы сохранены в: {abs_file}")
    
    # Сохраняем погрешности
    errors_file = results_dir / f"errors_{date_str}.csv"
    errors_df = pd.DataFrame(errors)
    errors_df.to_csv(errors_file, index=False)
    print(f"✓ Погрешности сохранены в: {errors_file}")
    
    # Сохраняем сводную статистику
    stats = {
        'date': date_str,
        'avg_error_percent': np.mean([e['abs_error_percent'] for e in errors]),
        'max_error_percent': np.max([e['abs_error_percent'] for e in errors]),
        'min_error_percent': np.min([e['abs_error_percent'] for e in errors]),
        'num_pairs': len(errors),
        'num_currencies': len(absolute_rates)
    }
    
    stats_file = results_dir / f"stats_{date_str}.json"
    import json
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"✓ Статистика сохранена в: {stats_file}")

def analyze_arbitrage_opportunities(actual_rates, pair_list):
    """Анализирует арбитражные возможности"""
    print("\n" + "=" * 80)
    print("АНАЛИЗ АРБИТРАЖНЫХ ВОЗМОЖНОСТЕЙ")
    print("=" * 80)
    
    # Проверяем тождество для треугольного арбитража
    if len(pair_list) >= 3:
        # Ищем треугольники (A/B, B/C, A/C)
        for i, pair1 in enumerate(pair_list):
            for j, pair2 in enumerate(pair_list):
                if i >= j:
                    continue
                
                cur1a, cur1b = pair1[:3], pair1[3:]
                cur2a, cur2b = pair2[:3], pair2[3:]
                
                # Ищем третью пару, которая замыкает треугольник
                possible_pairs = [
                    f"{cur1a}{cur2b}",  # A/C
                    f"{cur2b}{cur1a}",  # C/A
                    f"{cur1b}{cur2a}",  # B/D (если D есть)
                    f"{cur2a}{cur1b}"   # D/B
                ]
                
                for pair3 in possible_pairs:
                    if pair3 in actual_rates:
                        # Вычисляем теоретический курс
                        if pair3 == f"{cur1a}{cur2b}":
                            theoretical = actual_rates[pair1] / actual_rates[pair2]
                        elif pair3 == f"{cur2b}{cur1a}":
                            theoretical = 1 / (actual_rates[pair1] / actual_rates[pair2])
                        elif pair3 == f"{cur1b}{cur2a}":
                            theoretical = actual_rates[pair2] / actual_rates[pair1]
                        else:  # pair3 == f"{cur2a}{cur1b}"
                            theoretical = 1 / (actual_rates[pair2] / actual_rates[pair1])
                        
                        actual = actual_rates[pair3]
                        diff_percent = ((actual - theoretical) / actual) * 100
                        
                        print(f"\nТреугольник: {pair1} → {pair2} → {pair3}")
                        print(f"  Теоретический {pair3}: {theoretical:.6f}")
                        print(f"  Фактический {pair3}:   {actual:.6f}")
                        print(f"  Разница: {diff_percent:.4f}%")
                        
                        if abs(diff_percent) > 0.1:
                            print(f"  ⚠ ВОЗМОЖНОСТЬ АРБИТРАЖА!")
                        break

def main():
    print("=" * 80)
    print("Шаг 4: Детальный расчет погрешностей для одной даты")
    print("=" * 80)
    
    # Конфигурация
    date_str = "2023-12-01"
    pairs = ['EURUSD', 'USDJPY', 'EURJPY']
    
    print(f"\nДата анализа: {date_str}")
    print(f"Анализируемые пары: {', '.join(pairs)}")
    
    # Решаем систему для даты
    print("\n" + "-" * 80)
    print("Решение системы уравнений...")
    
    result = solve_for_date(date_str, pairs)
    if result[0] is None:
        print("Не удалось решить систему!")
        return
    
    absolute_rates, actual_rates, pair_list, currency_list, a = result
    
    print("✓ Система решена успешно")
    print(f"  Найдено валют: {len(currency_list)}")
    print(f"  Найдено пар: {len(pair_list)}")
    
    # Выводим абсолютные курсы
    print("\n" + "-" * 80)
    print("АБСОЛЮТНЫЕ ВАЛЮТНЫЕ КУРСЫ (USD = 1.0):")
    print("-" * 80)
    
    for currency, rate in sorted(absolute_rates.items()):
        if currency == 'USD':
            print(f"  {currency}: {rate:.8f} (базовая валюта)")
        else:
            print(f"  {currency}: {rate:.8f}")
    
    # Вычисляем погрешности
    print("\n" + "-" * 80)
    print("ВЫЧИСЛЕНИЕ ПОГРЕШНОСТЕЙ...")
    
    errors = calculate_detailed_errors(absolute_rates, actual_rates, pair_list)
    
    # Выводим таблицу погрешностей
    print_error_table(errors)
    
    # Анализируем арбитражные возможности
    analyze_arbitrage_opportunities(actual_rates, pair_list)
    
    # Сохраняем результаты в файлы
    print("\n" + "-" * 80)
    print("СОХРАНЕНИЕ РЕЗУЛЬТАТОВ...")
    
    save_results_to_files(date_str, absolute_rates, errors)
    
    # Дополнительный анализ
    print("\n" + "-" * 80)
    print("ДОПОЛНИТЕЛЬНЫЙ АНАЛИЗ:")
    
    # Проверяем, какая пара имеет наибольший вклад в погрешность
    if errors:
        max_error_pair = max(errors, key=lambda x: x['abs_error_percent'])
        min_error_pair = min(errors, key=lambda x: x['abs_error_percent'])
        
        print(f"\n  Наибольшая погрешность: {max_error_pair['pair']} ({max_error_pair['error_percent']:.6f}%)")
        print(f"  Наименьшая погрешность: {min_error_pair['pair']} ({min_error_pair['error_percent']:.6f}%)")
        
        # Анализируем распределение погрешностей
        errors_by_pair = {e['pair']: e['error_percent'] for e in errors}
        print(f"\n  Распределение погрешностей по парам:")
        for pair, error in sorted(errors_by_pair.items()):
            sign = "+" if error > 0 else ""
            print(f"    {pair}: {sign}{error:.6f}%")
    
    print("\n" + "=" * 80)
    print("Шаг 4 завершен успешно!")
    print("=" * 80)
    print("\nСледующий шаг: Обработка нескольких дат")

if __name__ == "__main__":
    main()
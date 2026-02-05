#!/usr/bin/env python3
"""
Шаг 3: Решение СЛАУ для одной даты
Запуск из корневого каталога: python scripts/absolute_calculation/step3_solve_equation.py
"""

import pandas as pd
import numpy as np
from pathlib import Path

def load_pair_data(pair_name):
    """
    Загружает данные для одной валютной пары
    """
    try:
        root_dir = Path(__file__).parent.parent.parent
        file_path = root_dir / "data" / "raw" / "twelve_data" / "pairs" / f"{pair_name}.csv"
        
        if not file_path.exists():
            return None
        
        df = pd.read_csv(file_path)
        
        if 'datetime' in df.columns:
            df = df.rename(columns={'datetime': 'timestamp'})
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        
        return df
    
    except Exception as e:
        print(f"  Ошибка при загрузке {pair_name}: {e}")
        return None

def build_matrix_and_vector(pairs_data, date_str):
    """
    Строит матрицу M и вектор p для заданной даты
    """
    date_dt = pd.to_datetime(date_str)
    
    # Собираем данные для этой даты
    date_data = {}
    for pair_name, df in pairs_data.items():
        if df is not None and date_dt in df.index:
            close_price = df.loc[date_dt, 'close']
            if pd.notna(close_price):
                date_data[pair_name] = close_price
    
    if len(date_data) < 2:
        return None, None, None, None
    
    # Получаем уникальные валюты
    currencies = set()
    for pair in date_data.keys():
        cur1, cur2 = pair[:3], pair[3:]
        currencies.add(cur1)
        currencies.add(cur2)
    
    # Сортируем валюты и пары для детерминированного порядка
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
    
    # Создаем вектор p (логарифмы парных курсов)
    p = np.array([np.log(date_data[pair]) for pair in pair_list])
    
    return M, p, currency_list, pair_list, date_data

def solve_least_squares(M, p):
    """
    Решает систему M·a = p методом наименьших квадратов
    """
    try:
        # Решаем систему
        a, residuals, rank, s = np.linalg.lstsq(M, p, rcond=None)
        
        # Нормализуем решение (вычитаем среднее для стабильности)
        a_normalized = a - np.mean(a)
        
        return a_normalized, residuals
        
    except Exception as e:
        print(f"  Ошибка при решении СЛАУ: {e}")
        return None, None

def calculate_absolute_rates(a, currency_list):
    """
    Вычисляет абсолютные курсы из логарифмов
    """
    absolute_rates = {}
    for i, currency in enumerate(currency_list):
        # Экспонента от логарифма дает абсолютный курс
        absolute_rates[currency] = np.exp(a[i])
    
    return absolute_rates

def calculate_pair_rates_from_absolute(absolute_rates, pair_list):
    """
    Вычисляет парные курсы из абсолютных
    """
    calculated_rates = {}
    for pair in pair_list:
        cur1, cur2 = pair[:3], pair[3:]
        if cur1 in absolute_rates and cur2 in absolute_rates:
            calculated_rates[pair] = absolute_rates[cur1] / absolute_rates[cur2]
    
    return calculated_rates

def calculate_errors(actual_rates, calculated_rates):
    """
    Вычисляет относительные погрешности в процентах
    """
    errors = {}
    for pair in actual_rates:
        if pair in calculated_rates:
            actual = actual_rates[pair]
            calculated = calculated_rates[pair]
            error_percent = ((actual - calculated) / actual) * 100
            errors[pair] = error_percent
    
    return errors

def main():
    print("=" * 60)
    print("Шаг 3: Решение СЛАУ для одной даты")
    print("=" * 60)
    
    # 1. Загружаем данные для трех пар
    pairs = ['EURUSD', 'USDJPY', 'EURJPY']
    pairs_data = {}
    
    print("\nЗагрузка данных для пар:")
    for pair in pairs:
        df = load_pair_data(pair)
        if df is not None:
            pairs_data[pair] = df
            print(f"  ✓ {pair}: загружено")
        else:
            print(f"  ✗ {pair}: не удалось загрузить")
    
    # 2. Выбираем дату (используем ту же, что и в шаге 2)
    selected_date = "2023-12-01"
    print(f"\nВыбранная дата для анализа: {selected_date}")
    
    # 3. Строим матрицу M и вектор p
    print("\nПостроение матрицы и вектора...")
    result = build_matrix_and_vector(pairs_data, selected_date)
    
    if result[0] is None:
        print("Не удалось построить матрицу и вектор!")
        return
    
    M, p, currency_list, pair_list, actual_rates = result
    
    print(f"  Матрица M размером {M.shape[0]}×{M.shape[1]}")
    print(f"  Вектор p размером {p.shape[0]}")
    print(f"  Валюты: {currency_list}")
    print(f"  Пары: {pair_list}")
    
    # Выводим вектор p (логарифмы фактических курсов)
    print(f"\nВектор p (логарифмы фактических курсов):")
    for i, pair in enumerate(pair_list):
        print(f"  ln({pair}) = ln({actual_rates[pair]:.6f}) = {p[i]:.8f}")
    
    # 4. Решаем систему M·a = p
    print("\n" + "-" * 60)
    print("Решение системы M·a = p методом наименьших квадратов...")
    
    a, residuals = solve_least_squares(M, p)
    
    if a is None:
        print("Не удалось решить систему!")
        return
    
    print(f"  Вектор решения a (логарифмы абсолютных курсов):")
    for i, currency in enumerate(currency_list):
        print(f"  {currency}: a = {a[i]:.8f}")
    
    # 5. Вычисляем абсолютные курсы
    print("\n" + "-" * 60)
    print("Вычисление абсолютных курсов...")
    
    absolute_rates = calculate_absolute_rates(a, currency_list)
    
    print("Абсолютные курсы (до нормализации):")
    for currency, rate in absolute_rates.items():
        print(f"  {currency}: {rate:.8f}")
    
    # 6. Нормализуем абсолютные курсы (делаем USD = 1)
    print("\nНормализация (USD = 1.0):")
    if 'USD' in absolute_rates:
        usd_rate = absolute_rates['USD']
        for currency in absolute_rates:
            absolute_rates[currency] = absolute_rates[currency] / usd_rate
        
        print("Абсолютные курсы после нормализации:")
        for currency, rate in absolute_rates.items():
            print(f"  {currency}: {rate:.8f}")
    else:
        print("  USD не найден в списке валют, нормализация невозможна")
    
    # 7. Вычисляем парные курсы из абсолютных
    print("\n" + "-" * 60)
    print("Вычисление парных курсов из абсолютных...")
    
    calculated_rates = calculate_pair_rates_from_absolute(absolute_rates, pair_list)
    
    print("Сравнение фактических и рассчитанных парных курсов:")
    for pair in pair_list:
        actual = actual_rates[pair]
        calculated = calculated_rates.get(pair, 0)
        print(f"  {pair}: фактический = {actual:.6f}, рассчитанный = {calculated:.6f}")
    
    # 8. Вычисляем погрешности
    print("\n" + "-" * 60)
    print("Вычисление погрешностей...")
    
    errors = calculate_errors(actual_rates, calculated_rates)
    
    print("Относительные погрешности в процентах:")
    for pair, error in errors.items():
        print(f"  {pair}: {error:.8f}%")
    
    # 9. Статистика
    print("\n" + "-" * 60)
    print("Статистика:")
    
    if errors:
        error_values = list(errors.values())
        abs_errors = [abs(e) for e in error_values]
        
        print(f"  Средняя абсолютная погрешность: {np.mean(abs_errors):.8f}%")
        print(f"  Максимальная абсолютная погрешность: {np.max(abs_errors):.8f}%")
        print(f"  Минимальная абсолютная погрешность: {np.min(abs_errors):.8f}%")
        
        if residuals is not None and len(residuals) > 0:
            print(f"  Невязка решения (residuals): {residuals[0]:.12f}")
    
    # 10. Проверка согласованности
    print("\n" + "-" * 60)
    print("Проверка математической согласованности:")
    
    # Вычисляем M·a
    Ma = np.dot(M, a)
    
    print("  M·a (должен быть близок к p):")
    for i, pair in enumerate(pair_list):
        diff = abs(Ma[i] - p[i])
        print(f"    {pair}: M·a = {Ma[i]:.8f}, p = {p[i]:.8f}, разница = {diff:.12f}")
    
    # Проверяем тождество EURJPY = EURUSD × USDJPY
    if 'EURJPY' in actual_rates and 'EURUSD' in actual_rates and 'USDJPY' in actual_rates:
        actual_eurjpy = actual_rates['EURJPY']
        calculated_eurjpy = actual_rates['EURUSD'] * actual_rates['USDJPY']
        diff_percent = ((actual_eurjpy - calculated_eurjpy) / actual_eurjpy) * 100
        
        print(f"\n  Проверка тождества EURJPY = EURUSD × USDJPY:")
        print(f"    Фактический EURJPY: {actual_eurjpy:.6f}")
        print(f"    EURUSD × USDJPY: {calculated_eurjpy:.6f}")
        print(f"    Разница: {abs(actual_eurjpy - calculated_eurjpy):.6f} ({diff_percent:.4f}%)")
    
    print("\n" + "=" * 60)
    print("Шаг 3 завершен успешно!")
    print("=" * 60)
    print("\nСледующий шаг: Расчет погрешностей для одной даты")

if __name__ == "__main__":
    main()
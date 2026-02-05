"""
Вспомогательные функции для прототипа
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path
import json


def load_pair_data(pair_symbol):
    """
    Загружает данные для одной валютной пары
    
    Args:
        pair_symbol (str): Символ пары (например, 'EURUSD')
        
    Returns:
        pd.DataFrame: DataFrame с данными или None при ошибке
    """
    try:
        # Определяем путь к файлу
        root_dir = Path(__file__).parent.parent.parent
        pair_dir = root_dir / "data" / "raw" / "twelve_data" / "pairs"
        csv_file = pair_dir / f"{pair_symbol}.csv"
        
        if not csv_file.exists():
            return None
        
        # Загружаем CSV
        df = pd.read_csv(csv_file)
        
        # Преобразуем timestamp в datetime и устанавливаем как индекс
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df.index.name = 'date'
        
        # Сортируем по дате
        df.sort_index(inplace=True)
        
        return df
    
    except Exception as e:
        print(f"Ошибка при загрузке данных для {pair_symbol}: {e}")
        return None


def build_incidence_matrix(date_data):
    """
    Строит матрицу инцидентности для заданных пар на дату
    
    Args:
        date_data (dict): Словарь {pair: close_price}
        
    Returns:
        tuple: (матрица M, список валют, список пар)
    """
    if not date_data:
        return None, [], []
    
    # Получаем уникальные валюты
    currencies = set()
    for pair in date_data.keys():
        cur1, cur2 = pair[:3], pair[3:]
        currencies.add(cur1)
        currencies.add(cur2)
    
    # Сортируем валюты для детерминированного порядка
    currency_list = sorted(list(currencies))
    pair_list = sorted(list(date_data.keys()))
    
    # Создаем словарь для быстрого доступа к индексам валют
    currency_to_idx = {curr: i for i, curr in enumerate(currency_list)}
    
    # Инициализируем матрицу (пары × валюты)
    m = len(pair_list)
    n = len(currency_list)
    M = np.zeros((m, n))
    
    # Заполняем матрицу
    for i, pair in enumerate(pair_list):
        cur1, cur2 = pair[:3], pair[3:]
        
        # Валюта в числителе получает +1
        if cur1 in currency_to_idx:
            M[i, currency_to_idx[cur1]] = 1
        
        # Валюта в знаменателе получает -1
        if cur2 in currency_to_idx:
            M[i, currency_to_idx[cur2]] = -1
    
    return M, currency_list, pair_list


def solve_least_squares(M, p):
    """
    Решает систему M·a = p методом наименьших квадратов
    
    Args:
        M (np.array): Матрица инцидентности
        p (np.array): Вектор логарифмов парных курсов
        
    Returns:
        np.array: Вектор логарифмов абсолютных курсов или None при ошибке
    """
    try:
        # Используем SVD для устойчивого решения
        a, residuals, rank, s = np.linalg.lstsq(M, p, rcond=None)
        
        # Проверяем, что решение найдено
        if len(a) == 0:
            return None
        
        # Нормализуем решение (фиксируем масштаб)
        # Вычитаем среднее, чтобы получить значения относительно нулевого уровня
        a_normalized = a - np.mean(a)
        
        return a_normalized
    
    except Exception as e:
        print(f"Ошибка при решении МНК: {e}")
        return None


def calculate_errors(date_data, absolute_rates, pair_list):
    """
    Вычисляет относительные погрешности для каждой пары
    
    Args:
        date_data (dict): Фактические курсы пар {pair: actual_price}
        absolute_rates (dict): Абсолютные курсы валют {currency: absolute_value}
        pair_list (list): Список пар для расчета
        
    Returns:
        dict: Словарь с погрешностями {pair: error_data}
    """
    errors = {}
    
    for pair in pair_list:
        if pair not in date_data:
            continue
        
        cur1, cur2 = pair[:3], pair[3:]
        
        if cur1 not in absolute_rates or cur2 not in absolute_rates:
            continue
        
        actual_price = date_data[pair]
        
        # Вычисляем теоретический курс из абсолютных значений
        calculated_price = absolute_rates[cur1] / absolute_rates[cur2]
        
        # Вычисляем относительную погрешность в процентах
        error_percent = ((actual_price - calculated_price) / actual_price) * 100
        
        # Сохраняем с округлением
        errors[pair] = {
            'actual_value': round(actual_price, 6),
            'calculated_value': round(calculated_price, 6),
            'error_percent': round(error_percent, 6)
        }
    
    return errors


def save_daily_results(date_str, absolute_rates, output_dir):
    """
    Сохраняет абсолютные курсы для конкретной даты
    
    Args:
        date_str (str): Дата в формате 'YYYY-MM-DD'
        absolute_rates (dict): Словарь абсолютных курсов {currency: value}
        output_dir (Path): Директория для сохранения
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Создаем DataFrame
    df = pd.DataFrame.from_dict(absolute_rates, orient='index', columns=['absolute_value'])
    df.index.name = 'currency'
    df = df.reset_index()
    
    # Сохраняем в CSV
    output_file = output_dir / f"{date_str}.csv"
    df.to_csv(output_file, index=False)


def save_error_results(date_str, errors, output_dir):
    """
    Сохраняет погрешности для конкретной даты
    
    Args:
        date_str (str): Дата в формате 'YYYY-MM-DD'
        errors (dict): Словарь погрешностей {pair: error_data}
        output_dir (Path): Директория для сохранения
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not errors:
        return
    
    # Преобразуем словарь в DataFrame
    rows = []
    for pair, error_data in errors.items():
        rows.append({
            'pair': pair,
            'actual_value': error_data['actual_value'],
            'calculated_value': error_data['calculated_value'],
            'error_percent': error_data['error_percent']
        })
    
    df = pd.DataFrame(rows)
    
    # Сохраняем в CSV
    output_file = output_dir / f"{date_str}.csv"
    df.to_csv(output_file, index=False)
#!/usr/bin/env python3
"""
Шаг 2: Загрузка данных для 3 пар и построение матрицы для одной даты
Запуск из корневого каталога: python scripts/absolute_calculation/step2_build_matrix.py
"""

import pandas as pd
import numpy as np
from pathlib import Path

def load_pair_data(pair_name):
    """
    Загружает данные для одной валютной пары
    
    Args:
        pair_name (str): Название пары (например, 'EURUSD')
    
    Returns:
        pd.DataFrame: DataFrame с данными или None при ошибке
    """
    try:
        # Определяем путь к файлу
        root_dir = Path(__file__).parent.parent.parent
        file_path = root_dir / "data" / "raw" / "twelve_data" / "pairs" / f"{pair_name}.csv"
        
        if not file_path.exists():
            print(f"  Файл не найден: {file_path}")
            return None
        
        # Загружаем данные
        df = pd.read_csv(file_path)
        
        # Переименовываем 'datetime' в 'timestamp' для единообразия
        if 'datetime' in df.columns:
            df = df.rename(columns={'datetime': 'timestamp'})
        
        # Преобразуем timestamp в datetime и устанавливаем как индекс
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Сортируем по дате
        df.sort_index(inplace=True)
        
        # Оставляем только нужные колонки (убираем volume, если его нет)
        required_cols = ['open', 'high', 'low', 'close']
        available_cols = [col for col in required_cols if col in df.columns]
        df = df[available_cols]
        
        return df
    
    except Exception as e:
        print(f"  Ошибка при загрузке {pair_name}: {e}")
        return None

def get_available_date(pairs_data, target_date="2023-12-01"):
    """
    Находит дату, для которой есть данные во всех парах
    
    Args:
        pairs_data (dict): Словарь с данными пар
        target_date (str): Предпочтительная дата
    
    Returns:
        str: Дата в формате 'YYYY-MM-DD' или None
    """
    # Преобразуем target_date в datetime
    target_dt = pd.to_datetime(target_date)
    
    # Проверяем предпочтительную дату
    all_have_data = True
    for pair_name, df in pairs_data.items():
        if df is None or target_dt not in df.index:
            print(f"  {pair_name}: нет данных на {target_date}")
            all_have_data = False
    
    if all_have_data:
        return target_date
    
    # Ищем альтернативную дату (последнюю общую дату)
    print("\nПоиск альтернативной даты с данными для всех пар...")
    
    # Собираем все даты, которые есть в каждой паре
    common_dates = None
    for pair_name, df in pairs_data.items():
        if df is not None:
            pair_dates = set(df.index.strftime('%Y-%m-%d'))
            if common_dates is None:
                common_dates = pair_dates
            else:
                common_dates = common_dates.intersection(pair_dates)
    
    if not common_dates:
        print("  Нет общих дат для всех пар!")
        return None
    
    # Выбираем самую позднюю общую дату
    latest_date = max(common_dates)
    print(f"  Найдена общая дата: {latest_date}")
    return latest_date

def build_incidence_matrix(pairs_data, date_str):
    """
    Строит матрицу инцидентности для заданных пар на конкретную дату
    
    Args:
        pairs_data (dict): Словарь с данными пар
        date_str (str): Дата в формате 'YYYY-MM-DD'
    
    Returns:
        tuple: (матрица M, список валют, список пар)
    """
    # Преобразуем дату
    date_dt = pd.to_datetime(date_str)
    
    # Собираем данные для этой даты
    date_data = {}
    for pair_name, df in pairs_data.items():
        if df is not None and date_dt in df.index:
            close_price = df.loc[date_dt, 'close']
            if pd.notna(close_price):
                date_data[pair_name] = close_price
    
    print(f"\nДанные на {date_str}:")
    for pair, price in date_data.items():
        print(f"  {pair}: {price}")
    
    if len(date_data) < 2:
        print("  Недостаточно данных для построения матрицы")
        return None, [], []
    
    # Получаем уникальные валюты
    currencies = set()
    for pair in date_data.keys():
        # Разделяем пару на две валюты (каждая по 3 символа)
        cur1, cur2 = pair[:3], pair[3:]
        currencies.add(cur1)
        currencies.add(cur2)
    
    print(f"\nУникальные валюты: {sorted(list(currencies))}")
    
    # Сортируем валюты и пары для детерминированного порядка
    currency_list = sorted(list(currencies))
    pair_list = sorted(list(date_data.keys()))
    
    # Создаем словарь для быстрого доступа к индексам валют
    currency_to_idx = {curr: i for i, curr in enumerate(currency_list)}
    
    # Инициализируем матрицу (пары × валюты)
    m = len(pair_list)
    n = len(currency_list)
    M = np.zeros((m, n))
    
    # Заполняем матрицу
    print("\nПостроение матрицы M:")
    for i, pair in enumerate(pair_list):
        cur1, cur2 = pair[:3], pair[3:]
        
        # Валюта в числителе получает +1
        if cur1 in currency_to_idx:
            M[i, currency_to_idx[cur1]] = 1
            print(f"  {pair}: {cur1}(+1) / {cur2}(-1)")
        
        # Валюта в знаменателе получает -1
        if cur2 in currency_to_idx:
            M[i, currency_to_idx[cur2]] = -1
    
    return M, currency_list, pair_list

def main():
    print("=" * 60)
    print("Шаг 2: Загрузка данных для 3 пар и построение матрицы")
    print("=" * 60)
    
    # 1. Загружаем данные для трех пар
    pairs = ['EURUSD', 'USDJPY', 'EURJPY']
    pairs_data = {}
    
    print("\nЗагрузка данных для пар:")
    for pair in pairs:
        print(f"\n{pair}:")
        df = load_pair_data(pair)
        if df is not None:
            pairs_data[pair] = df
            print(f"  Загружено {len(df)} строк")
            print(f"  Диапазон дат: {df.index[0].date()} - {df.index[-1].date()}")
        else:
            print(f"  Не удалось загрузить данные")
            pairs_data[pair] = None
    
    # 2. Находим дату, для которой есть данные во всех парах
    print("\n" + "-" * 60)
    print("Поиск даты с данными для всех пар...")
    
    # Пробуем несколько возможных дат
    test_dates = ["2023-12-01", "2023-06-01", "2022-12-01", "2021-12-01"]
    
    selected_date = None
    for test_date in test_dates:
        selected_date = get_available_date(pairs_data, test_date)
        if selected_date:
            break
    
    if not selected_date:
        print("Не удалось найти дату с данными для всех пар!")
        return
    
    print(f"\nВыбрана дата для анализа: {selected_date}")
    
    # 3. Строим матрицу инцидентности
    print("\n" + "-" * 60)
    print("Построение матрицы инцидентности:")
    
    M, currencies, pairs_in_matrix = build_incidence_matrix(pairs_data, selected_date)
    
    if M is None:
        print("Не удалось построить матрицу!")
        return
    
    # 4. Выводим информацию о матрице
    print(f"\nМатрица M ({M.shape[0]} строк × {M.shape[1]} столбцов):")
    print(M)
    
    print(f"\nСтруктура матрицы:")
    print(f"  Строки (пары): {pairs_in_matrix}")
    print(f"  Столбцы (валюты): {currencies}")
    
    print("\nДетализация строк матрицы:")
    for i, pair in enumerate(pairs_in_matrix):
        row_str = f"  {pair}: "
        for j, currency in enumerate(currencies):
            if M[i, j] != 0:
                row_str += f"{currency}({int(M[i, j])}) "
        print(row_str)
    
    # 5. Проверяем свойства матрицы
    print("\n" + "-" * 60)
    print("Проверка свойств матрицы:")
    
    # Проверяем, что каждая строка имеет ровно два ненулевых элемента
    for i, row in enumerate(M):
        non_zero = np.nonzero(row)[0]
        if len(non_zero) != 2:
            print(f"  ⚠ Строка {i} ({pairs_in_matrix[i]}) имеет {len(non_zero)} ненулевых элементов")
        else:
            print(f"  ✓ Строка {i} ({pairs_in_matrix[i]}): OK")
    
    # Проверяем сумму элементов в каждой строке
    row_sums = M.sum(axis=1)
    if np.allclose(row_sums, 0):
        print("  ✓ Сумма элементов в каждой строке равна 0 (корректно)")
    else:
        print(f"  ⚠ Суммы строк: {row_sums}")
    
    print("\n" + "=" * 60)
    print("Шаг 2 завершен успешно!")
    print("=" * 60)
    print("\nСледующий шаг: Решение СЛАУ для одной даты")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Шаг 5: Обработка нескольких дат
Запуск из корневого каталога: python scripts/absolute_calculation/step5_multiple_dates.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from datetime import datetime, timedelta
import json

# Добавляем путь к корневому каталогу для импорта
sys.path.insert(0, str(Path(__file__).parent))

def load_pair_data(pair_name):
    """Загружает данные для одной валютной пары"""
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
        print(f"  ✗ Ошибка при загрузке {pair_name}: {e}")
        return None

def solve_system_for_date(date_str, pairs_data, pairs):
    """Решает систему для указанной даты"""
    date_dt = pd.to_datetime(date_str)
    
    # Собираем данные на дату
    date_data = {}
    for pair in pairs:
        df = pairs_data.get(pair)
        if df is not None and date_dt in df.index:
            close_price = df.loc[date_dt, 'close']
            if pd.notna(close_price):
                date_data[pair] = close_price
    
    if len(date_data) < 2:
        return None, None, None, None
    
    # Получаем уникальные валюты
    currencies = set()
    for pair in date_data.keys():
        cur1, cur2 = pair[:3], pair[3:]
        currencies.add(cur1)
        currencies.add(cur2)
    
    currency_list = sorted(list(currencies))
    pair_list = sorted(list(date_data.keys()))
    
    # Строим матрицу M
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
        
        # Вычисляем погрешности
        errors = {}
        for pair in pair_list:
            cur1, cur2 = pair[:3], pair[3:]
            if cur1 in absolute_rates and cur2 in absolute_rates:
                actual = date_data[pair]
                calculated = absolute_rates[cur1] / absolute_rates[cur2]
                error_percent = ((actual - calculated) / actual) * 100
                errors[pair] = error_percent
        
        return absolute_rates, date_data, errors, pair_list
    
    except Exception as e:
        print(f"  ✗ Ошибка при решении системы: {e}")
        return None, None, None, None

def generate_date_range(start_date_str, num_days=7):
    """Генерирует список дат начиная с указанной"""
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    dates = []
    
    for i in range(num_days):
        current_date = start_date + timedelta(days=i)
        dates.append(current_date.strftime("%Y-%m-%d"))
    
    return dates

def process_dates(date_range, pairs):
    """Обрабатывает список дат"""
    print("Загрузка данных для всех пар...")
    
    # Загружаем данные для всех пар один раз
    pairs_data = {}
    for pair in pairs:
        df = load_pair_data(pair)
        if df is not None:
            pairs_data[pair] = df
            print(f"  ✓ {pair}: загружено {len(df)} строк")
        else:
            print(f"  ✗ {pair}: не удалось загрузить")
    
    print(f"\nОбработка {len(date_range)} дат...")
    
    results = []
    for date_str in date_range:
        print(f"\nДата: {date_str}")
        
        absolute_rates, date_data, errors, pair_list = solve_system_for_date(
            date_str, pairs_data, pairs
        )
        
        if absolute_rates is None:
            print("  ✗ Пропуск (недостаточно данных)")
            continue
        
        # Статистика по погрешностям
        if errors:
            error_values = list(errors.values())
            abs_errors = [abs(e) for e in error_values]
            avg_error = np.mean(abs_errors)
            max_error = np.max(abs_errors)
        else:
            avg_error = max_error = 0.0
        
        # Сохраняем результат
        result = {
            'date': date_str,
            'absolute_rates': absolute_rates,
            'actual_rates': date_data,
            'errors': errors,
            'avg_error': avg_error,
            'max_error': max_error,
            'num_pairs': len(pair_list),
            'num_currencies': len(absolute_rates)
        }
        
        results.append(result)
        
        print(f"  ✓ Обработано: {len(absolute_rates)} валют, {len(pair_list)} пар")
        print(f"    Средняя погрешность: {avg_error:.6f}%, Максимальная: {max_error:.6f}%")
    
    return results

def save_daily_results(results):
    """Сохраняет ежедневные результаты"""
    base_dir = Path(__file__).parent.parent.parent / "data" / "absolute" / "step5_results"
    base_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nСохранение ежедневных результатов в: {base_dir}")
    
    # Сохраняем каждую дату отдельно
    for result in results:
        date_str = result['date']
        
        # Абсолютные курсы
        abs_file = base_dir / f"absolute_rates_{date_str}.csv"
        abs_df = pd.DataFrame.from_dict(
            result['absolute_rates'], 
            orient='index', 
            columns=['absolute_value']
        )
        abs_df.index.name = 'currency'
        abs_df.to_csv(abs_file)
        
        # Фактические парные курсы
        actual_file = base_dir / f"actual_rates_{date_str}.csv"
        actual_df = pd.DataFrame.from_dict(
            result['actual_rates'], 
            orient='index', 
            columns=['close_price']
        )
        actual_df.index.name = 'pair'
        actual_df.to_csv(actual_file)
        
        # Погрешности
        errors_file = base_dir / f"errors_{date_str}.csv"
        errors_df = pd.DataFrame.from_dict(
            result['errors'], 
            orient='index', 
            columns=['error_percent']
        )
        errors_df.index.name = 'pair'
        errors_df.to_csv(errors_file)
    
    print(f"  ✓ Сохранено {len(results)} дат")

def save_summary_results(results):
    """Сохраняет сводные результаты"""
    base_dir = Path(__file__).parent.parent.parent / "data" / "absolute" / "step5_results"
    
    # Сводная таблица абсолютных курсов по дням
    print("\nСоздание сводных таблиц...")
    
    # 1. Таблица абсолютных курсов (валюта × дата)
    abs_summary = {}
    for result in results:
        date_str = result['date']
        for currency, rate in result['absolute_rates'].items():
            if currency not in abs_summary:
                abs_summary[currency] = {}
            abs_summary[currency][date_str] = rate
    
    abs_summary_df = pd.DataFrame(abs_summary).T
    abs_summary_file = base_dir / "summary_absolute_rates.csv"
    abs_summary_df.to_csv(abs_summary_file)
    print(f"  ✓ Сводная таблица абсолютных курсов: {abs_summary_file}")
    
    # 2. Таблица погрешностей по дням
    error_summary = {}
    for result in results:
        date_str = result['date']
        for pair, error in result['errors'].items():
            if pair not in error_summary:
                error_summary[pair] = {}
            error_summary[pair][date_str] = error
    
    error_summary_df = pd.DataFrame(error_summary).T
    error_summary_file = base_dir / "summary_errors.csv"
    error_summary_df.to_csv(error_summary_file)
    print(f"  ✓ Сводная таблица погрешностей: {error_summary_file}")
    
    # 3. Статистика по дням
    stats_data = []
    for result in results:
        stats_data.append({
            'date': result['date'],
            'avg_error': result['avg_error'],
            'max_error': result['max_error'],
            'num_pairs': result['num_pairs'],
            'num_currencies': result['num_currencies']
        })
    
    stats_df = pd.DataFrame(stats_data)
    stats_file = base_dir / "daily_statistics.csv"
    stats_df.to_csv(stats_file, index=False)
    print(f"  ✓ Статистика по дням: {stats_file}")
    
    # 4. Общая статистика
    if results:
        overall_stats = {
            'total_dates_processed': len(results),
            'overall_avg_error': np.mean([r['avg_error'] for r in results]),
            'overall_max_error': np.max([r['max_error'] for r in results]),
            'min_avg_error': np.min([r['avg_error'] for r in results]),
            'max_avg_error': np.max([r['avg_error'] for r in results]),
            'currencies_found': sorted(list(results[0]['absolute_rates'].keys())),
            'pairs_found': sorted(list(results[0]['actual_rates'].keys()))
        }
        
        stats_file = base_dir / "overall_statistics.json"
        with open(stats_file, 'w') as f:
            json.dump(overall_stats, f, indent=2, default=str)
        print(f"  ✓ Общая статистика: {stats_file}")

def analyze_trends(results):
    """Анализирует тренды изменения абсолютных курсов"""
    if not results:
        return
    
    print("\n" + "=" * 80)
    print("АНАЛИЗ ТРЕНДОВ АБСОЛЮТНЫХ КУРСОВ")
    print("=" * 80)
    
    # Собираем данные для анализа
    dates = [r['date'] for r in results]
    
    # Анализ по каждой валюте
    currencies = sorted(list(results[0]['absolute_rates'].keys()))
    
    print(f"\nИзменение абсолютных курсов за период:")
    for currency in currencies:
        rates = [r['absolute_rates'][currency] for r in results]
        change = ((rates[-1] - rates[0]) / rates[0]) * 100
        
        print(f"\n  {currency}:")
        print(f"    Начало: {rates[0]:.6f}")
        print(f"    Конец:  {rates[-1]:.6f}")
        print(f"    Изменение: {change:.4f}%")
        
        if abs(change) > 1.0:
            direction = "рост" if change > 0 else "падение"
            print(f"    ⚠ Значительный {direction}!")
    
    # Анализ погрешностей
    print(f"\n\nИзменение погрешностей за период:")
    avg_errors = [r['avg_error'] for r in results]
    max_errors = [r['max_error'] for r in results]
    
    print(f"  Средняя погрешность:")
    print(f"    Начало: {avg_errors[0]:.6f}%")
    print(f"    Конец:  {avg_errors[-1]:.6f}%")
    print(f"    Изменение: {((avg_errors[-1] - avg_errors[0]) / avg_errors[0] * 100):.2f}%")
    
    print(f"\n  Максимальная погрешность:")
    print(f"    Начало: {max_errors[0]:.6f}%")
    print(f"    Конец:  {max_errors[-1]:.6f}%")
    print(f"    Изменение: {((max_errors[-1] - max_errors[0]) / max_errors[0] * 100):.2f}%")
    
    # Стабильность алгоритма
    print(f"\n\nСТАБИЛЬНОСТЬ АЛГОРИТМА:")
    avg_error_std = np.std(avg_errors)
    max_error_std = np.std(max_errors)
    
    print(f"  Стандартное отклонение средней погрешности: {avg_error_std:.6f}%")
    print(f"  Стандартное отклонение максимальной погрешности: {max_error_std:.6f}%")
    
    if avg_error_std < 0.01:
        print("  ✅ Алгоритм работает стабильно")
    elif avg_error_std < 0.1:
        print("  ⚠ Умеренная изменчивость погрешностей")
    else:
        print("  ⚠ Высокая изменчивость погрешностей")

def main():
    print("=" * 80)
    print("Шаг 5: Обработка нескольких дат")
    print("=" * 80)
    
    # Конфигурация
    start_date = "2023-12-01"
    num_days = 7
    pairs = ['EURUSD', 'USDJPY', 'EURJPY']
    
    print(f"\nКонфигурация:")
    print(f"  Начальная дата: {start_date}")
    print(f"  Количество дней: {num_days}")
    print(f"  Пары: {', '.join(pairs)}")
    
    # Генерируем список дат
    date_range = generate_date_range(start_date, num_days)
    print(f"\nДиапазон дат: {date_range[0]} - {date_range[-1]}")
    
    # Обрабатываем все даты
    results = process_dates(date_range, pairs)
    
    if not results:
        print("\n✗ Не удалось обработать ни одной даты!")
        return
    
    print(f"\n✓ Успешно обработано {len(results)} из {len(date_range)} дат")
    
    # Сохраняем результаты
    save_daily_results(results)
    save_summary_results(results)
    
    # Анализируем тренды
    analyze_trends(results)
    
    # Выводим краткий отчет
    print("\n" + "=" * 80)
    print("КРАТКИЙ ОТЧЕТ")
    print("=" * 80)
    
    if results:
        dates_processed = [r['date'] for r in results]
        avg_errors = [r['avg_error'] for r in results]
        
        print(f"\nОбработанные даты: {', '.join(dates_processed)}")
        print(f"\nДиапазон средней погрешности: {min(avg_errors):.6f}% - {max(avg_errors):.6f}%")
        print(f"Средняя погрешность за период: {np.mean(avg_errors):.6f}%")
        
        # Качество результатов
        overall_avg = np.mean(avg_errors)
        if overall_avg < 0.01:
            quality = "ОТЛИЧНО"
        elif overall_avg < 0.1:
            quality = "ХОРОШО"
        elif overall_avg < 1.0:
            quality = "УДОВЛЕТВОРИТЕЛЬНО"
        else:
            quality = "ПЛОХО"
        
        print(f"\nОЦЕНКА КАЧЕСТВА: {quality}")
    
    print("\n" + "=" * 80)
    print("Шаг 5 завершен успешно!")
    print("=" * 80)
    print("\nСледующий шаг: Масштабирование на 10 пар")

if __name__ == "__main__":
    main()
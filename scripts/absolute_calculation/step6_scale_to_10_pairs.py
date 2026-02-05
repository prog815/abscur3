#!/usr/bin/env python3
"""
Шаг 6: Масштабирование на 10 пар
Запуск из корневого каталога: python scripts/absolute_calculation/step6_scale_to_10_pairs.py
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

def solve_system_for_date(date_str, pairs_data, all_pairs):
    """Решает систему для указанной даты для всех доступных пар"""
    date_dt = pd.to_datetime(date_str)
    
    # Собираем данные на дату
    date_data = {}
    available_pairs = []
    
    for pair in all_pairs:
        df = pairs_data.get(pair)
        if df is not None and date_dt in df.index:
            close_price = df.loc[date_dt, 'close']
            if pd.notna(close_price):
                date_data[pair] = close_price
                available_pairs.append(pair)
    
    if len(date_data) < 5:  # Минимум 5 пар для устойчивого решения
        return None, None, None, None, None
    
    # Получаем уникальные валюты
    currencies = set()
    for pair in available_pairs:
        cur1, cur2 = pair[:3], pair[3:]
        currencies.add(cur1)
        currencies.add(cur2)
    
    if len(currencies) < 5:  # Минимум 5 валют
        return None, None, None, None, None
    
    currency_list = sorted(list(currencies))
    pair_list = sorted(available_pairs)
    
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
        
        # Вычисляем погрешности для всех пар
        errors = {}
        for pair in pair_list:
            cur1, cur2 = pair[:3], pair[3:]
            if cur1 in absolute_rates and cur2 in absolute_rates:
                actual = date_data[pair]
                calculated = absolute_rates[cur1] / absolute_rates[cur2]
                error_percent = ((actual - calculated) / actual) * 100
                errors[pair] = error_percent
        
        return absolute_rates, date_data, errors, pair_list, currency_list
    
    except Exception as e:
        print(f"  ✗ Ошибка при решении системы: {e}")
        return None, None, None, None, None

def generate_date_range(start_date_str, num_days=7):
    """Генерирует список дат начиная с указанной"""
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    dates = []
    
    for i in range(num_days):
        current_date = start_date + timedelta(days=i)
        dates.append(current_date.strftime("%Y-%m-%d"))
    
    return dates

def process_dates_with_10_pairs(date_range, pairs_10):
    """Обрабатывает список дат для 10 пар"""
    print("Загрузка данных для 10 пар...")
    
    # Загружаем данные для всех пар один раз
    pairs_data = {}
    loaded_count = 0
    
    for pair in pairs_10:
        df = load_pair_data(pair)
        if df is not None:
            pairs_data[pair] = df
            loaded_count += 1
            print(f"  ✓ {pair}: загружено {len(df)} строк")
        else:
            print(f"  ✗ {pair}: не удалось загрузить")
    
    print(f"\nУспешно загружено: {loaded_count} из {len(pairs_10)} пар")
    
    results = []
    for date_str in date_range:
        print(f"\nДата: {date_str}")
        
        absolute_rates, date_data, errors, pair_list, currency_list = solve_system_for_date(
            date_str, pairs_data, pairs_10
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
            min_error = np.min(abs_errors)
        else:
            avg_error = max_error = min_error = 0.0
        
        # Сохраняем результат
        result = {
            'date': date_str,
            'absolute_rates': absolute_rates,
            'actual_rates': date_data,
            'errors': errors,
            'avg_error': avg_error,
            'max_error': max_error,
            'min_error': min_error,
            'num_pairs': len(pair_list),
            'num_currencies': len(currency_list),
            'currency_list': currency_list,
            'pair_list': pair_list
        }
        
        results.append(result)
        
        print(f"  ✓ Обработано: {len(currency_list)} валют, {len(pair_list)} пар")
        print(f"    Погрешности: средняя={avg_error:.6f}%, макс={max_error:.6f}%, мин={min_error:.6f}%")
    
    return results

def compare_with_3_pairs(results_10, results_3):
    """Сравнивает результаты 10 пар с результатами 3 пар"""
    print("\n" + "=" * 80)
    print("СРАВНЕНИЕ 3 ПАР vs 10 ПАР")
    print("=" * 80)
    
    if not results_10 or not results_3:
        print("Недостаточно данных для сравнения")
        return
    
    # Создаем словари для быстрого доступа по дате
    dict_10 = {r['date']: r for r in results_10}
    dict_3 = {r['date']: r for r in results_3}
    
    common_dates = set(dict_10.keys()) & set(dict_3.keys())
    
    if not common_dates:
        print("Нет общих дат для сравнения")
        return
    
    print(f"\nОбщие даты для сравнения: {sorted(common_dates)}")
    
    comparison_data = []
    
    for date in sorted(common_dates):
        r10 = dict_10[date]
        r3 = dict_3[date]
        
        improvement = ((r3['avg_error'] - r10['avg_error']) / r3['avg_error']) * 100
        
        comparison_data.append({
            'date': date,
            'avg_error_3': r3['avg_error'],
            'avg_error_10': r10['avg_error'],
            'improvement': improvement,
            'num_pairs_3': r3['num_pairs'],
            'num_pairs_10': r10['num_pairs'],
            'num_currencies_3': r3['num_currencies'],
            'num_currencies_10': r10['num_currencies']
        })
        
        print(f"\nДата: {date}")
        print(f"  3 пар:  {r3['num_pairs']} пар, {r3['num_currencies']} валют, погрешность={r3['avg_error']:.6f}%")
        print(f"  10 пар: {r10['num_pairs']} пар, {r10['num_currencies']} валют, погрешность={r10['avg_error']:.6f}%")
        print(f"  Улучшение: {improvement:.2f}%")
    
    # Общая статистика улучшения
    if comparison_data:
        avg_improvement = np.mean([c['improvement'] for c in comparison_data])
        max_improvement = np.max([c['improvement'] for c in comparison_data])
        min_improvement = np.min([c['improvement'] for c in comparison_data])
        
        print(f"\n\nОБЩАЯ СТАТИСТИКА УЛУЧШЕНИЯ:")
        print(f"  Среднее улучшение точности: {avg_improvement:.2f}%")
        print(f"  Максимальное улучшение: {max_improvement:.2f}%")
        print(f"  Минимальное улучшение: {min_improvement:.2f}%")
        
        if avg_improvement > 0:
            print(f"\n  ✅ Увеличение количества пар УЛУЧШАЕТ точность!")
        else:
            print(f"\n  ⚠ Увеличение количества пар НЕ улучшает точность")
        
        # Сохраняем сравнение в файл
        base_dir = Path(__file__).parent.parent.parent / "data" / "absolute" / "step6_results"
        base_dir.mkdir(parents=True, exist_ok=True)
        
        comparison_df = pd.DataFrame(comparison_data)
        comparison_file = base_dir / "comparison_3_vs_10.csv"
        comparison_df.to_csv(comparison_file, index=False)
        print(f"\n  ✓ Таблица сравнения сохранена: {comparison_file}")

def analyze_pair_coverage(results_10):
    """Анализирует покрытие данных по парам"""
    if not results_10:
        return
    
    print("\n" + "=" * 80)
    print("АНАЛИЗ ПОКРЫТИЯ ДАННЫХ ПО ПАРАМ")
    print("=" * 80)
    
    # Собираем статистику по парам
    pair_stats = {}
    all_pairs = set()
    
    for result in results_10:
        for pair in result['pair_list']:
            if pair not in pair_stats:
                pair_stats[pair] = 0
            pair_stats[pair] += 1
    
    # Выводим статистику
    print(f"\nКоличество дней с данными для каждой пары:")
    for pair, count in sorted(pair_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(results_10)) * 100
        print(f"  {pair}: {count} дней ({percentage:.1f}%)")
    
    # Анализируем валюты
    print(f"\nЧастота валют в расчетах:")
    currency_stats = {}
    for result in results_10:
        for currency in result['currency_list']:
            if currency not in currency_stats:
                currency_stats[currency] = 0
            currency_stats[currency] += 1
    
    for currency, count in sorted(currency_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(results_10)) * 100
        print(f"  {currency}: {count} дней ({percentage:.1f}%)")
    
    # Сохраняем статистику покрытия
    base_dir = Path(__file__).parent.parent.parent / "data" / "absolute" / "step6_results"
    
    coverage_df = pd.DataFrame([
        {'pair': pair, 'days_with_data': count, 'coverage_percent': (count / len(results_10)) * 100}
        for pair, count in pair_stats.items()
    ])
    
    coverage_file = base_dir / "pair_coverage_statistics.csv"
    coverage_df.to_csv(coverage_file, index=False)
    print(f"\n✓ Статистика покрытия сохранена: {coverage_file}")

def save_results_10_pairs(results):
    """Сохраняет результаты для 10 пар"""
    base_dir = Path(__file__).parent.parent.parent / "data" / "absolute" / "step6_results"
    base_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nСохранение результатов для 10 пар в: {base_dir}")
    
    # Сохраняем каждую дату отдельно
    for result in results:
        date_str = result['date']
        
        # Абсолютные курсы
        abs_file = base_dir / f"absolute_rates_10_{date_str}.csv"
        abs_df = pd.DataFrame.from_dict(
            result['absolute_rates'], 
            orient='index', 
            columns=['absolute_value']
        )
        abs_df.index.name = 'currency'
        abs_df.to_csv(abs_file)
        
        # Погрешности
        errors_file = base_dir / f"errors_10_{date_str}.csv"
        errors_df = pd.DataFrame.from_dict(
            result['errors'], 
            orient='index', 
            columns=['error_percent']
        )
        errors_df.index.name = 'pair'
        errors_df.to_csv(errors_file)
    
    # Сводная статистика
    if results:
        stats_data = []
        for result in results:
            stats_data.append({
                'date': result['date'],
                'avg_error': result['avg_error'],
                'max_error': result['max_error'],
                'min_error': result['min_error'],
                'num_pairs': result['num_pairs'],
                'num_currencies': result['num_currencies'],
                'currencies': ','.join(result['currency_list']),
                'pairs': ','.join(result['pair_list'])
            })
        
        stats_df = pd.DataFrame(stats_data)
        stats_file = base_dir / "daily_statistics_10.csv"
        stats_df.to_csv(stats_file, index=False)
        print(f"  ✓ Ежедневная статистика сохранена: {stats_file}")
        
        # Общая статистика
        overall_stats = {
            'total_dates_processed': len(results),
            'avg_avg_error': np.mean([r['avg_error'] for r in results]),
            'avg_max_error': np.mean([r['max_error'] for r in results]),
            'avg_min_error': np.mean([r['min_error'] for r in results]),
            'avg_num_pairs': np.mean([r['num_pairs'] for r in results]),
            'avg_num_currencies': np.mean([r['num_currencies'] for r in results]),
            'all_currencies_found': sorted(list(set().union(*[r['currency_list'] for r in results]))),
            'all_pairs_found': sorted(list(set().union(*[r['pair_list'] for r in results])))
        }
        
        overall_file = base_dir / "overall_statistics_10.json"
        with open(overall_file, 'w') as f:
            json.dump(overall_stats, f, indent=2, default=str)
        print(f"  ✓ Общая статистика сохранена: {overall_file}")

def load_3_pairs_results():
    """Загружает результаты для 3 пар из Шага 5"""
    results_dir = Path(__file__).parent.parent.parent / "data" / "absolute" / "step5_results"
    
    if not results_dir.exists():
        print("Директория с результатами Шага 5 не найдена!")
        return []
    
    # Ищем файл статистики
    stats_file = results_dir / "daily_statistics.csv"
    if not stats_file.exists():
        print("Файл статистики Шага 5 не найден!")
        return []
    
    try:
        stats_df = pd.read_csv(stats_file)
        
        results = []
        for _, row in stats_df.iterrows():
            # Загружаем абсолютные курсы
            abs_file = results_dir / f"absolute_rates_{row['date']}.csv"
            if abs_file.exists():
                abs_df = pd.read_csv(abs_file)
                absolute_rates = dict(zip(abs_df['currency'], abs_df['absolute_value']))
                
                # Загружаем погрешности
                errors_file = results_dir / f"errors_{row['date']}.csv"
                if errors_file.exists():
                    errors_df = pd.read_csv(errors_file)
                    errors = dict(zip(errors_df['pair'], errors_df['error_percent']))
                    
                    results.append({
                        'date': row['date'],
                        'absolute_rates': absolute_rates,
                        'errors': errors,
                        'avg_error': row['avg_error'],
                        'max_error': row['max_error'],
                        'num_pairs': row['num_pairs'],
                        'num_currencies': row['num_currencies']
                    })
        
        return results
    
    except Exception as e:
        print(f"Ошибка при загрузке результатов Шага 5: {e}")
        return []

def main():
    print("=" * 80)
    print("Шаг 6: Масштабирование на 10 пар")
    print("=" * 80)
    
    # Конфигурация
    start_date = "2023-12-01"
    num_days = 7
    
    # Список из 10 пар
    pairs_10 = [
        'EURUSD',  # Евро/Доллар
        'USDJPY',  # Доллар/Йена
        'GBPUSD',  # Фунт/Доллар
        'USDCHF',  # Доллар/Франк
        'AUDUSD',  # Австралийский доллар/Доллар
        'USDCAD',  # Доллар/Канадский доллар
        'NZDUSD',  # Новозеландский доллар/Доллар
        'EURGBP',  # Евро/Фунт
        'EURJPY',  # Евро/Йена
        'GBPJPY',  # Фунт/Йена
    ]
    
    print(f"\nКонфигурация:")
    print(f"  Начальная дата: {start_date}")
    print(f"  Количество дней: {num_days}")
    print(f"  Количество пар: {len(pairs_10)}")
    print(f"  Пары: {', '.join(pairs_10[:5])}...")
    
    # Генерируем список дат
    date_range = generate_date_range(start_date, num_days)
    print(f"\nДиапазон дат: {date_range[0]} - {date_range[-1]}")
    
    # Обрабатываем все даты для 10 пар
    results_10 = process_dates_with_10_pairs(date_range, pairs_10)
    
    if not results_10:
        print("\n✗ Не удалось обработать ни одной даты!")
        return
    
    print(f"\n✓ Успешно обработано {len(results_10)} из {len(date_range)} дат")
    
    # Сохраняем результаты для 10 пар
    save_results_10_pairs(results_10)
    
    # Загружаем результаты для 3 пар из Шага 5
    print("\nЗагрузка результатов для 3 пар из Шага 5...")
    results_3 = load_3_pairs_results()
    
    if results_3:
        print(f"  Загружено результатов для {len(results_3)} дат")
        # Сравниваем результаты
        compare_with_3_pairs(results_10, results_3)
    else:
        print("  Не удалось загрузить результаты для 3 пар")
    
    # Анализируем покрытие данных
    analyze_pair_coverage(results_10)
    
    # Выводим итоговый отчет
    print("\n" + "=" * 80)
    print("ИТОГОВЫЙ ОТЧЕТ ШАГА 6")
    print("=" * 80)
    
    if results_10:
        avg_errors = [r['avg_error'] for r in results_10]
        avg_pairs = [r['num_pairs'] for r in results_10]
        avg_currencies = [r['num_currencies'] for r in results_10]
        
        print(f"\nСтатистика для 10 пар:")
        print(f"  Средняя погрешность за период: {np.mean(avg_errors):.6f}%")
        print(f"  Диапазон погрешностей: {min(avg_errors):.6f}% - {max(avg_errors):.6f}%")
        print(f"  Среднее количество пар в расчетах: {np.mean(avg_pairs):.1f}")
        print(f"  Среднее количество валют в расчетах: {np.mean(avg_currencies):.1f}")
        
        # Определяем качество
        overall_avg_error = np.mean(avg_errors)
        if overall_avg_error < 0.01:
            quality = "ОТЛИЧНО"
        elif overall_avg_error < 0.1:
            quality = "ХОРОШО"
        elif overall_avg_error < 1.0:
            quality = "УДОВЛЕТВОРИТЕЛЬНО"
        else:
            quality = "ПЛОХО"
        
        print(f"\nОЦЕНКА КАЧЕСТВА: {quality}")
        
        # Рекомендации
        print(f"\nРЕКОМЕНДАЦИИ:")
        if overall_avg_error < 0.1:
            print("  ✅ Точность достаточна для перехода к следующему этапу")
        else:
            print("  ⚠ Рекомендуется дополнительная оптимизация перед переходом")
        
        if np.mean(avg_pairs) < 8:
            print("  ⚠ Не все пары используются в расчетах. Проверьте качество данных.")
        else:
            print("  ✅ Большинство пар используется в расчетах")
    
    print("\n" + "=" * 80)
    print("Шаг 6 завершен успешно!")
    print("=" * 80)
    print("\nСледующий шаг: Создание структуры хранения")

if __name__ == "__main__":
    main()
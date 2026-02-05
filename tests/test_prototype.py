#!/usr/bin/env python3
"""
Базовые тесты для прототипа расчета абсолютных курсов
"""

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from scripts.absolute_calculation.utils import (
    build_incidence_matrix,
    solve_least_squares,
    calculate_errors
)


def test_build_incidence_matrix():
    """Тест построения матрицы инцидентности"""
    print("Тест 1: Построение матрицы инцидентности")
    
    # Тестовые данные
    date_data = {
        "EURUSD": 1.1000,
        "USDJPY": 150.00,
        "EURJPY": 165.00
    }
    
    M, currencies, pairs = build_incidence_matrix(date_data)
    
    assert M is not None
    assert len(currencies) == 3  # EUR, USD, JPY
    assert len(pairs) == 3
    
    # Проверяем структуру матрицы
    assert M.shape == (3, 3)
    
    # EURUSD: EUR(+1), USD(-1)
    # USDJPY: USD(+1), JPY(-1) 
    # EURJPY: EUR(+1), JPY(-1)
    
    print("  ✓ Матрица построена корректно")
    print(f"  Валюты: {currencies}")
    print(f"  Пары: {pairs}")
    print(f"  Размер матрицы: {M.shape}\n")


def test_solve_least_squares():
    """Тест решения методом наименьших квадратов"""
    print("Тест 2: Решение методом наименьших квадратов")
    
    # Создаем тестовую матрицу и вектор
    M = np.array([
        [1, -1, 0],   # EUR/USD
        [0, 1, -1],   # USD/JPY
        [1, 0, -1]    # EUR/JPY
    ])
    
    # Тестовые логарифмы курсов
    p = np.array([
        np.log(1.1000),   # EUR/USD
        np.log(150.00),   # USD/JPY
        np.log(165.00)    # EUR/JPY
    ])
    
    a = solve_least_squares(M, p)
    
    assert a is not None
    assert len(a) == 3
    
    print("  ✓ Система решена корректно")
    print(f"  Решение (логарифмы): {a}\n")


def test_calculate_errors():
    """Тест расчета погрешностей"""
    print("Тест 3: Расчет погрешностей")
    
    date_data = {
        "EURUSD": 1.1000,
        "USDJPY": 150.00
    }
    
    absolute_rates = {
        "EUR": 1.1,
        "USD": 1.0,
        "JPY": 0.00666667  # 1/150
    }
    
    errors = calculate_errors(date_data, absolute_rates, ["EURUSD", "USDJPY"])
    
    assert "EURUSD" in errors
    assert "USDJPY" in errors
    
    # Теоретические значения должны быть близки к фактическим
    eur_usd_error = errors["EURUSD"]["error_percent"]
    usd_jpy_error = errors["USDJPY"]["error_percent"]
    
    assert abs(eur_usd_error) < 0.1  # Погрешность < 0.1%
    assert abs(usd_jpy_error) < 0.1
    
    print("  ✓ Погрешности рассчитаны корректно")
    print(f"  EURUSD погрешность: {eur_usd_error:.6f}%")
    print(f"  USDJPY погрешность: {usd_jpy_error:.6f}%\n")


def test_integration():
    """Интеграционный тест"""
    print("Тест 4: Интеграционный тест")
    
    # Создаем согласованные данные
    # Пусть абсолютные курсы: EUR=1.2, USD=1.0, JPY=0.008
    abs_rates = {"EUR": 1.2, "USD": 1.0, "JPY": 0.008}
    
    # Рассчитываем парные курсы из абсолютных
    date_data = {
        "EURUSD": abs_rates["EUR"] / abs_rates["USD"],
        "USDJPY": abs_rates["USD"] / abs_rates["JPY"],
        "EURJPY": abs_rates["EUR"] / abs_rates["JPY"]
    }
    
    # Добавляем небольшой шум
    for pair in date_data:
        date_data[pair] *= 1.0001  # +0.01% шум
    
    # Строим матрицу
    M, currencies, pairs = build_incidence_matrix(date_data)
    
    # Формируем вектор p
    p = np.array([np.log(date_data[pair]) for pair in pairs])
    
    # Решаем
    a = solve_least_squares(M, p)
    
    # Вычисляем абсолютные курсы из решения
    calculated_rates = {curr: np.exp(val) for curr, val in zip(currencies, a)}
    
    # Вычисляем погрешности
    errors = calculate_errors(date_data, calculated_rates, pairs)
    
    # Погрешности должны быть малы
    max_error = max(abs(errors[pair]["error_percent"]) for pair in errors)
    
    assert max_error < 0.02  # Погрешность < 0.02%
    
    print("  ✓ Интеграционный тест пройден")
    print(f"  Максимальная погрешность: {max_error:.6f}%")
    
    # Выводим сравнение
    print("\n  Сравнение абсолютных курсов:")
    for curr in abs_rates:
        if curr in calculated_rates:
            orig = abs_rates[curr]
            calc = calculated_rates[curr]
            diff = abs((calc - orig) / orig * 100)
            print(f"    {curr}: исходный={orig:.6f}, рассчитанный={calc:.6f}, разница={diff:.6f}%")


def run_all_tests():
    """Запуск всех тестов"""
    print("=" * 60)
    print("Запуск тестов для прототипа")
    print("=" * 60)
    
    try:
        test_build_incidence_matrix()
        test_solve_least_squares()
        test_calculate_errors()
        test_integration()
        
        print("=" * 60)
        print("✓ Все тесты пройдены успешно!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ Тест не пройден: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Ошибка при выполнении тестов: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
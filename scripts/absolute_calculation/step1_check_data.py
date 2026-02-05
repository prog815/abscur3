#!/usr/bin/env python3
"""
Шаг 1: Проверка окружения и загрузка данных для одной пары
Запуск из корневого каталога: python scripts/absolute_calculation/step1_check_data.py
"""

import os
import sys
import pandas as pd
from pathlib import Path

def main():
    print("=" * 60)
    print("Шаг 1: Проверка окружения и загрузка данных")
    print("=" * 60)
    
    # 1. Проверяем, что мы в корневом каталоге
    current_dir = Path(__file__).parent.parent.parent
    print(f"Текущий каталог проекта: {current_dir}")
    
    # 2. Определяем путь к данным
    data_file = current_dir / "data" / "raw" / "twelve_data" / "pairs" / "EURUSD.csv"
    print(f"Путь к файлу данных: {data_file}")
    
    # 3. Проверяем существование файла
    if not data_file.exists():
        print("✗ ОШИБКА: Файл не найден!")
        print("  Убедитесь, что вы запускаете скрипт из корневого каталога проекта")
        print("  и что данные парных курсов загружены в правильную директорию")
        print(f"  Ожидаемый путь: {data_file}")
        return
    
    print("✓ Файл найден")
    
    # 4. Пытаемся загрузить данные
    try:
        df = pd.read_csv(data_file)
        print(f"✓ Данные загружены успешно")
        print(f"  Размер данных: {df.shape[0]} строк, {df.shape[1]} колонок")
        
        # 5. Выводим информацию о данных
        print("\nПервые 5 строк данных:")
        print(df.head())
        
        print("\nИнформация о колонках:")
        print(df.dtypes)
        
        print("\nСтатистика по колонке 'close':")
        if 'close' in df.columns:
            print(f"  Минимум: {df['close'].min():.6f}")
            print(f"  Максимум: {df['close'].max():.6f}")
            print(f"  Среднее: {df['close'].mean():.6f}")
        
        # 6. Проверяем наличие необходимых колонок
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            print(f"\n⚠ Предупреждение: отсутствуют колонки: {missing_columns}")
        else:
            print("\n✓ Все необходимые колонки присутствуют")
        
        # 7. Проверяем диапазон дат
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            print(f"\nДиапазон дат в данных:")
            print(f"  От: {df['timestamp'].min()}")
            print(f"  До: {df['timestamp'].max()}")
            
        # 8. Проверяем пропущенные значения
        missing_values = df.isnull().sum()
        if missing_values.sum() > 0:
            print(f"\n⚠ Предупреждение: есть пропущенные значения:")
            for col, count in missing_values[missing_values > 0].items():
                print(f"  {col}: {count} пропущенных значений")
        
    except Exception as e:
        print(f"✗ ОШИБКА при загрузке данных: {e}")
        print("\nВозможные причины:")
        print("1. Файл поврежден или имеет неправильный формат")
        print("2. Проблемы с кодировкой файла")
        print("3. Недостаточно памяти для загрузки")
        return
    
    print("\n" + "=" * 60)
    print("Шаг 1 завершен успешно!")
    print("=" * 60)
    print("\nСледующий шаг: Загрузка данных для 3 пар и построение матрицы")

if __name__ == "__main__":
    main()
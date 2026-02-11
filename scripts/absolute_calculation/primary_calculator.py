#!/usr/bin/env python3
"""
primary_calculator.py – Шаг 2.1: Адаптация каркаса под реальную структуру данных.
Задачи:
- Загрузить список пар из data/metadata/currency_pairs.json
- Преобразовать EUR_USD → EURUSD.csv
- Проверить существование файлов в data/raw/twelve_data/pairs/
- Определить общий диапазон дат по первым нескольким парам (без полной загрузки)
"""

import sys
print("=== СКРИПТ ЗАПУЩЕН ===", file=sys.stderr)
sys.stderr.flush()

import json
from pathlib import Path
import pandas as pd
from datetime import datetime

# ---------- Конфигурация путей (относительно корня проекта) ----------
PAIRS_JSON = Path("data/metadata/currency_pairs.json")
DATA_DIR = Path("data/raw/twelve_data/pairs")
CORE_CURRENCIES = {'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD'}

def load_pairs_list():
    """Загружает список валютных пар из JSON."""
    if not PAIRS_JSON.exists():
        raise FileNotFoundError(f"Файл не найден: {PAIRS_JSON}")
    with open(PAIRS_JSON, 'r', encoding='utf-8') as f:
        pairs = json.load(f)
    print(f"✅ Загружено пар из JSON: {len(pairs)}")
    return pairs

def convert_to_filename(pair):
    """Преобразует EUR_USD → EURUSD.csv."""
    return pair.replace("_", "") + ".csv"

def check_files_exist(pairs, data_dir):
    """Проверяет существование CSV-файлов для каждой пары."""
    existing = []
    missing = []
    for pair in pairs:
        filename = convert_to_filename(pair)
        filepath = data_dir / filename
        if filepath.exists():
            existing.append((pair, filepath))
        else:
            missing.append((pair, filepath))
    print(f"📁 Существующих файлов: {len(existing)}")
    print(f"❌ Отсутствует файлов: {len(missing)}")
    return existing, missing

def get_date_range_from_file(filepath, nrows=1000):
    """
    Быстро определяет минимальную и максимальную дату в CSV.
    Читает только столбец 'datetime', ограничиваясь первыми nrows строками.
    """
    try:
        # Пробуем прочитать только столбец datetime
        df = pd.read_csv(filepath, usecols=['datetime'], nrows=nrows)
        df['datetime'] = pd.to_datetime(df['datetime'])
        min_date = df['datetime'].min()
        max_date = df['datetime'].max()
        return min_date, max_date
    except Exception as e:
        print(f"⚠️  Ошибка при чтении {filepath.name}: {e}")
        return None, None

def main():
    print("=" * 60)
    print(" ШАГ 2.1 – Адаптация каркаса под реальную структуру данных")
    print("=" * 60)

    # 1. Загрузка списка пар
    try:
        pairs = load_pairs_list()
    except Exception as e:
        print(f"🚨 Критическая ошибка: {e}")
        return

    # 2. Проверка существования файлов
    existing_pairs, missing_pairs = check_files_exist(pairs, DATA_DIR)

    # 3. Демонстрация преобразования имён (первые 5)
    print("\n🔁 Примеры преобразования имён (первые 5):")
    for pair in pairs[:5]:
        print(f"   {pair:12} → {convert_to_filename(pair)}")

    # 4. Определение диапазона дат на основе первых 10 существующих файлов
    print("\n📅 Анализ дат (первые 10 существующих файлов):")
    global_min = None
    global_max = None

    for idx, (pair, filepath) in enumerate(existing_pairs[:10]):
        min_dt, max_dt = get_date_range_from_file(filepath)
        if min_dt and max_dt:
            print(f"   {pair:12} : {min_dt.date()} – {max_dt.date()}  ({filepath.name})")
            if global_min is None or min_dt < global_min:
                global_min = min_dt
            if global_max is None or max_dt > global_max:
                global_max = max_dt

    if global_min and global_max:
        print("\n🌍 Ориентировочный общий диапазон дат (по первым 10 файлам):")
        print(f"   С: {global_min.date()}  По: {global_max.date()}")
    else:
        print("\n⚠️  Не удалось определить диапазон дат.")

    # 5. Статистика по валютам (простая)
    all_currencies = set()
    for pair in pairs:
        base, quote = pair.split('_')
        all_currencies.add(base)
        all_currencies.add(quote)
    print(f"\n💰 Уникальных валют (всего): {len(all_currencies)}")
    core_available = all_currencies.intersection(CORE_CURRENCIES)
    print(f"   Ядро валют (USD,EUR,GBP,JPY,CHF,CAD,AUD):")
    print(f"   Доступно: {sorted(core_available)}")
    print(f"   Отсутствует: {sorted(CORE_CURRENCIES - core_available)}")

    print("\n✅ Шаг 2.1 завершён.")

if __name__ == "__main__":
    main()
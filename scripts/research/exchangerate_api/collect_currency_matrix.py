"""
СКРИПТ 1: Сбор матрицы валютных курсов с ExchangeRate-API.
Собирает данные для последующего анализа связей между валютами.
Внимание: для экономии лимита тестирует подмножество валют (по умолчанию 50).
"""
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Set
from dotenv import load_dotenv
import requests

# --- НАСТРОЙКА ---
current_dir = Path.cwd()
env_path = current_dir / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    print("❌ Файл .env не найден.")
    sys.exit(1)

API_KEY = os.getenv('EXCHANGERATE_API_KEY')
if not API_KEY:
    print("❌ Ключ API не найден.")
    sys.exit(1)

API_BASE_URL = "https://v6.exchangerate-api.com/v6"

# Список валют для тестирования. НАЧНИТЕ С МАЛОГО ДЛЯ ТЕСТА.
# Можно взять топ-50 по ликвидности или из вашего списка.
# Здесь пример - валюты из вашего проекта + основные мировые.
TEST_CURRENCIES = [
    'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD', 'CNY', 'HKD',
    'SGD', 'SEK', 'NOK', 'DKK', 'KRW', 'INR', 'BRL', 'RUB', 'ZAR', 'MXN',
    'AED', 'SAR', 'TRY', 'PLN', 'THB', 'IDR', 'CZK', 'HUF', 'ILS', 'CLP',
    'PHP', 'MYR', 'COP', 'PEN', 'VND', 'PKR', 'BDT', 'EGP', 'ARS', 'KZT',
    'UAH', 'KWD', 'QAR', 'RON', 'HUF', 'ISK', 'HRK', 'BGN', 'NOK', 'DKK'
]
# ВНИМАНИЕ: 50 валют * 50 запросов = 2500 запросов! Это превышает МЕСЯЧНЫЙ лимит.
# Поэтому скрипт по умолчанию использует РЕЖИМ ОБРАЗЦА (см. строку ~65).

# --- ФУНКЦИИ ---
def get_latest_rates(base_currency: str) -> Dict[str, float]:
    """Запрашивает последние курсы для базовой валюты. Возвращает словарь таргет->курс."""
    url = f"{API_BASE_URL}/{API_KEY}/latest/{base_currency}"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        if data.get('result') == 'success':
            # Возвращаем только числовые курсы
            return {k: v for k, v in data.get('conversion_rates', {}).items() if isinstance(v, (int, float))}
        else:
            print(f"   API Error for {base_currency}: {data.get('error-type')}")
            return {}
    except Exception as e:
        print(f"   Network/Other Error for {base_currency}: {e}")
        return {}

def collect_data(currencies_to_test: List[str], sample_mode: bool = True, sample_size: int = 15) -> Dict:
    """
    Основная функция сбора.
    sample_mode=True: тестирует только sample_size валют из списка для быстрой проверки логики.
    sample_mode=False: тестирует ВСЕ переданные валюты (осторожно!).
    """
    print("="*70)
    print("НАЧИНАЮ СБОР ДАННЫХ ДЛЯ ПОСТРОЕНИЯ МАТРИЦЫ СВЯЗЕЙ")
    print("="*70)

    if sample_mode:
        print(f"⚡ РЕЖИМ ОБРАЗЦА: тестирую {sample_size} из {len(currencies_to_test)} валют.")
        currencies_to_test = currencies_to_test[:sample_size]
    else:
        print(f"⚠️  ПОЛНЫЙ РЕЖИМ: тестирую все {len(currencies_to_test)} валют.")
        print("   Это может занять много времени и исчерпать месячную квоту!")

    collected_data = {}
    request_count = 0

    for i, base_currency in enumerate(currencies_to_test, 1):
        print(f"   [{i:3d}/{len(currencies_to_test)}] Запрашиваю курсы для базы: {base_currency}...")
        rates = get_latest_rates(base_currency)
        request_count += 1

        if rates:
            # Сохраняем только если получили хотя бы один курс
            collected_data[base_currency] = {
                "rates": rates,
                "targets_count": len(rates)
            }
        else:
            # Отмечаем базу как "неудачную" для анализа
            collected_data[base_currency] = {
                "rates": {},
                "targets_count": 0,
                "error": "no_valid_rates"
            }

        # КРИТИЧЕСКАЯ ПАУЗА для бесплатного тарифа и соблюдения лимитов
        # 0.5 сек ~ 2 запроса в секунду, 15 валют займет ~8 секунд + время ответа.
        time.sleep(0.5)

    print(f"\n✅ Сбор данных завершен.")
    print(f"   Сделано запросов: {request_count}")
    print(f"   Успешных баз (вернули курсы): {sum(1 for d in collected_data.values() if d['targets_count'] > 0)}")
    return collected_data

def save_collected_data(data: Dict, sample_mode: bool):
    """Сохраняет собранные данные в JSON файл с мета-информацией."""
    output_dir = current_dir / 'data' / 'research_results' / 'exchangerate_api'
    output_dir.mkdir(parents=True, exist_ok=True)

    # Формируем итоговый объект для сохранения
    dataset = {
        "meta": {
            "collection_timestamp": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "api_tested": "ExchangeRate-API",
            "plan": "Free",
            "sample_mode": sample_mode,
            "currencies_tested": list(data.keys()),
            "total_requests_simulated": len(data)  # По одному запросу на валюту
        },
        "matrix_data": data
    }

    filename = output_dir / f'currency_matrix_data_{"SAMPLE" if sample_mode else "FULL"}_{time.strftime("%Y%m%d_%H%M")}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print(f"📦 Данные сохранены в файл: {filename}")
    return filename

# --- ЗАПУСК ---
if __name__ == '__main__':
    # НАСТРОЙТЕ ЭТИ ПАРАМЕТРЫ ПЕРЕД ЗАПУСКОМ:
    USE_SAMPLE_MODE = True      # Поставьте False для сбора по всем TEST_CURRENCIES (осторожно!)
    SAMPLE_SIZE = 15            # Сколько валют проверить в режиме образца

    if not USE_SAMPLE_MODE:
        confirm = input(f"⚠️  Вы запускаете ПОЛНЫЙ режим для {len(TEST_CURRENCIES)} валют.\n   Это сделает ~{len(TEST_CURRENCIES)} запросов к API. Продолжить? (y/n): ")
        if confirm.lower() != 'y':
            print("Отмена. Запустите с USE_SAMPLE_MODE=True.")
            sys.exit(0)

    print("Старт сбора матрицы курсов...")
    collected_matrix = collect_data(TEST_CURRENCIES, sample_mode=USE_SAMPLE_MODE, sample_size=SAMPLE_SIZE)
    saved_file = save_collected_data(collected_matrix, USE_SAMPLE_MODE)

    print("\n" + "="*70)
    print("СБОР ДАННЫХ ЗАВЕРШЕН. ДАЛЬНЕЙШИЕ ШАГИ:")
    print("="*70)
    print("1. Файл с данными готов для анализа.")
    print("2. Следующий шаг — запустить скрипт АНАЛИЗА (analyze_currency_matrix.py).")
    print("3. Он загрузит файл", saved_file.name, "и построит матрицу связей.")
    print("="*70)
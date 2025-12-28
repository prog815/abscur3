"""
Полный анализ возможностей ExchangeRate-API для проекта AbsCur3.
Проверяет доступные валюты, базовые валюты и даёт рекомендации по стратегии.
"""
import os
import sys
import time
import json
import requests
from pathlib import Path
from typing import List, Dict, Set, Tuple
from dotenv import load_dotenv

# --- 1. НАСТРОЙКА И ЗАГРУЗКА ---
current_dir = Path.cwd()
env_path = current_dir / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print("✅ Переменные окружения загружены.")
else:
    print("❌ Файл .env не найден. Убедитесь, что он создан.")
    sys.exit(1)

API_KEY = os.getenv('EXCHANGERATE_API_KEY')
if not API_KEY:
    print("❌ Ключ API не найден.")
    sys.exit(1)

API_BASE_URL = "https://v6.exchangerate-api.com/v6"
SUPPORTED_CODES_URL = f"{API_BASE_URL}/{API_KEY}/codes"

# --- 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def fetch_supported_currencies() -> List[str]:
    """Запрос полного списка всех поддерживаемых валют (165 шт)."""
    print("\n1. ЗАПРАШИВАЮ ПОЛНЫЙ СПИСОК ВАЛЮТ API...")
    try:
        response = requests.get(SUPPORTED_CODES_URL, timeout=15)
        data = response.json()
        if data.get('result') == 'success':
            currencies = [item[0] for item in data['supported_codes']]
            print(f"   ✅ Получено {len(currencies)} валют.")
            return currencies
        else:
            print(f"   ❌ Ошибка API: {data.get('error-type')}")
            return []
    except Exception as e:
        print(f"   ❌ Ошибка сети: {e}")
        return []

def test_base_currency_availability(currency: str) -> Tuple[bool, Dict]:
    """Проверяет, может ли валюта быть базовой (использует эндпоинт /latest)."""
    url = f"{API_BASE_URL}/{API_KEY}/latest/{currency}"
    try:
        # Добавляем заголовок для уменьшения нагрузки на сервер
        response = requests.get(url, timeout=10, headers={'User-Agent': 'AbsCur3-Research/1.0'})
        data = response.json()
        if data.get('result') == 'success':
            return True, data.get('conversion_rates', {})
        else:
            # Тип ошибки поможет понять причину
            error_type = data.get('error-type')
            if error_type == 'unsupported-code':
                return False, {'error': 'unsupported-code'}
            # Другие ошибки (например, "quota-reached") могут быть временными
            return False, {'error': error_type}
    except requests.exceptions.RequestException as e:
        return False, {'error': str(e)}

def find_all_available_bases(all_currencies: List[str], sample_size: int = None) -> Tuple[List[str], Dict]:
    """
    Тестирует валюты на возможность быть базовой.
    Для ускорения можно протестировать выборку (sample_size).
    """
    print(f"\n2. ТЕСТИРУЮ ВАЛЮТЫ НА ВОЗМОЖНОСТЬ БЫТЬ БАЗОВОЙ...")
    if sample_size and sample_size < len(all_currencies):
        print(f"   ⚡ Режим быстрого теста: проверяю {sample_size} из {len(all_currencies)} валют.")
        currencies_to_test = all_currencies[:sample_size]
    else:
        currencies_to_test = all_currencies
        print(f"   ⚠️  Полный тест: {len(currencies_to_test)} запросов. Это может занять время.")

    available_bases = []
    base_coverage = {}  # Для каждой успешной базы сохраним количество доступных к ней валют

    for i, currency in enumerate(currencies_to_test, 1):
        print(f"   {i:3d}/{len(currencies_to_test)}: Тестирую {currency}...", end="\r")
        is_available, rates_data = test_base_currency_availability(currency)

        if is_available:
            available_bases.append(currency)
            # Сохраняем, сколько валют доступно относительно этой базы
            base_coverage[currency] = len(rates_data)
        else:
            base_coverage[currency] = 0

        # Критически важная пауза для бесплатного тарифа, чтобы не превысить лимиты частоты
        time.sleep(0.3)  # ~3 запроса в секунду

    print(f"\n   ✅ Завершено. Найдено доступных базовых валют: {len(available_bases)}")
    return available_bases, base_coverage

def analyze_and_save_results(all_currencies: List[str], available_bases: List[str], base_coverage: Dict):
    """Анализирует результаты и сохраняет их в JSON."""
    print(f"\n3. АНАЛИЗ РЕЗУЛЬТАТОВ...")

    # Разница между всеми валютами и доступными базами
    unavailable_as_base = [c for c in all_currencies if c not in available_bases]

    # Сортировка баз по покрытию (сколько валют доступны через эту базу)
    sorted_bases_by_coverage = sorted(
        [(base, cov) for base, cov in base_coverage.items() if cov > 0],
        key=lambda x: x[1],
        reverse=True
    )

    # Создание отчёта
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "api_tested": "ExchangeRate-API (Free Plan)",
        "total_currencies_supported": len(all_currencies),
        "available_base_currencies_count": len(available_bases),
        "available_base_currencies_list": available_bases,
        "unavailable_as_base_count": len(unavailable_as_base),
        "unavailable_as_base_list": unavailable_as_base,
        "base_coverage_ranking": [{"base": base, "targets_available": cov} for base, cov in sorted_bases_by_coverage],
        "analysis": {
            "daily_requests_for_full_matrix": len(available_bases),
            "monthly_requests_estimate_30d": len(available_bases) * 30,
            "free_plan_monthly_limit": 1500,
            "fits_free_plan": (len(available_bases) * 30) <= 1500
        }
    }

    # Сохранение отчёта
    output_dir = current_dir / 'data' / 'research_results' / 'exchangerate_api'
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f'base_currency_analysis_{time.strftime("%Y%m%d_%H%M")}.json'

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"   📊 Отчёт сохранён: {report_path}")
    return report

# --- 3. ГЛАВНАЯ ФУНКЦИЯ И ВЫВОД ---
def main():
    print("="*70)
    print("ПОЛНЫЙ АНАЛИЗ БАЗОВЫХ ВАЛЮТ EXCHANGERATE-API")
    print("="*70)

    # Шаг 1: Получаем все поддерживаемые валюты (список из 165)
    all_supported_currencies = fetch_supported_currencies()
    if not all_supported_currencies:
        print("Не удалось получить список валют. Завершение.")
        return

    # Шаг 2: Тестируем, какие из них могут быть базовыми
    # Для первого быстрого теста можно поставить sample_size=30.
    # Для окончательного - убрать аргумент sample_size.
    available_bases, coverage_data = find_all_available_bases(all_supported_currencies, sample_size=None)

    # Шаг 3: Анализируем и сохраняем
    report = analyze_and_save_results(all_supported_currencies, available_bases, coverage_data)

    # Шаг 4: Человекочитаемый вывод
    print("\n" + "="*70)
    print("КЛЮЧЕВЫЕ ВЫВОДЫ")
    print("="*70)
    print(f"• Всего валют в API: {report['total_currencies_supported']}")
    print(f"• Из них могут быть базовыми: {report['available_base_currencies_count']}")
    print(f"• Примеры доступных баз: {', '.join(report['available_base_currencies_list'][:10])}...")

    print(f"\n• Ежедневных запросов для полной матрицы: {report['analysis']['daily_requests_for_full_matrix']}")
    print(f"• Месячная нагрузка (30 дн.): ~{report['analysis']['monthly_requests_estimate_30d']} запросов")
    print(f"• Лимит бесплатного тарифа: {report['analysis']['free_plan_monthly_limit']} запросов/мес")

    if report['analysis']['fits_free_plan']:
        usage_percent = (report['analysis']['monthly_requests_estimate_30d'] / report['analysis']['free_plan_monthly_limit']) * 100
        print(f"✅ ВМЕЩАЕТСЯ В ЛИМИТ: будет использовано ~{usage_percent:.1f}% месячной квоты.")
    else:
        print(f"❌ ПРЕВЫШАЕТ ЛИМИТ. Нужна оптимизация или платный тариф.")

    # Рекомендация по покрытию
    if report['available_base_currencies_count'] > 50:
        print(f"\n💡 ВАЖНО: API позволяет использовать более 50 валют как базовые.")
        print("   Это открывает потенциал для роста проекта, но бесплатного тарифа")
        print("   может не хватить для ежедневного снятия полной матрицы.")
    print("="*70)

if __name__ == '__main__':
    main()
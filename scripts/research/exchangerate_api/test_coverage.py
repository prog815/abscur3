"""
Универсальный тест покрытия валют для ExchangeRate-API.
Предполагает, что запуск происходит из корня проекта.
"""
import os
import sys
import json
import requests
from pathlib import Path
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# ================== УПРОЩЕННАЯ ЛОГИКА ==================
# ПРЕДПОЛАГАЕМ, ЧТО ЗАПУСК ИЗ КОРНЯ ПРОЕКТА!
current_dir = Path.cwd()  # Текущая рабочая директория
env_path = current_dir / '.env'

print(f"📁 Запуск из директории: {current_dir}")
print(f"📁 Ищу .env по пути: {env_path}")

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"✅ Загружены переменные из .env")
else:
    print(f"ℹ️  Файл .env не найден. Использую системные переменные.")
# ======================================================

# --- Загружаем конфигурацию проекта ---
# currencies.py находится в scripts/research/currencies.py
currencies_path = current_dir / 'scripts' / 'research' / 'currencies.py'
print(f"📁 Ищу currencies.py по пути: {currencies_path}")

if currencies_path.exists():
    # Добавляем scripts/research в sys.path для импорта
    sys.path.insert(0, str(currencies_path.parent))
    try:
        from currencies import CURRENCIES, CURRENCY_NAMES
        print(f"✅ Загружено {len(CURRENCIES)} валют из модуля 'currencies'")
    except ImportError as e:
        print(f"⚠️  Ошибка загрузки currencies.py: {e}")
        CURRENCIES = []
else:
    print("⚠️  Файл currencies.py не найден.")
    CURRENCIES = []

# Если список валют пуст, используем тестовый
if not CURRENCIES:
    use_fallback = input("Использовать тестовый список валют? (y/n): ").lower()
    if use_fallback == 'y':
        # Ваш тестовый список валют
        CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'RUB', 'AED', 'KWD', 'UAH', 'KZT', 'CNY']
        print(f"Использую тестовый список из {len(CURRENCIES)} валют.")
    else:
        print("Завершаю выполнение.")
        sys.exit(1)

# --- Конфигурация API ---
ENV_VAR_NAME = 'EXCHANGERATE_API_KEY'
API_BASE_URL = 'https://v6.exchangerate-api.com/v6'

def get_api_key() -> str:
    """Безопасно получает API ключ из переменных окружения."""
    api_key = os.getenv(ENV_VAR_NAME)
    if not api_key:
        print(f"\n❌ FATAL: Не найдена переменная окружения '{ENV_VAR_NAME}'.")
        print("\nПРОВЕРЬТЕ:")
        print(f"1. Запускаете ли вы скрипт из корня проекта?")
        print(f"   Текущая директория: {current_dir}")
        print(f"2. Есть ли файл .env в этой директории?")
        print(f"3. Содержит ли он строку: EXCHANGERATE_API_KEY=ваш_ключ_тут")
        print(f"\nПример правильной структуры:")
        print(f"  {current_dir}/.env")
        print(f"  {current_dir}/scripts/research/exchangerate_api/test_coverage.py")
        sys.exit(1)
    
    # Проверяем формат ключа (должен начинаться с валидного префикса)
    if not (api_key.startswith('er-api-') or len(api_key) >= 20):
        print(f"⚠️  Внимание: Ключ выглядит нестандартно: {api_key[:10]}...")
    
    return api_key

def fetch_latest_rates(api_key: str, base_currency: str = 'USD') -> Dict:
    """Запрашивает последние курсы валют относительно базовой."""
    url = f"{API_BASE_URL}/{api_key}/latest/{base_currency}"
    try:
        print(f"🌐 Запрос: {url[:60]}...")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        # Проверяем, не вернулся ли HTML вместо JSON (например, страница ошибки)
        content_type = response.headers.get('content-type', '')
        if 'html' in content_type.lower():
            print(f"❌ API вернул HTML вместо JSON. Возможно, неверный ключ или URL.")
            return {}
            
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети при запросе к API: {e}")
        return {}
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка разбора ответа API (не JSON): {e}")
        return {}

def analyze_coverage(api_rates: Dict, project_currencies: List[str]) -> Tuple[List[str], List[str]]:
    """Анализирует, какие валюты проекта доступны в API."""
    if not api_rates:
        print("❌ Пустой ответ от API")
        return [], project_currencies.copy()
    
    if api_rates.get('result') != 'success':
        error_type = api_rates.get('error-type', 'unknown error')
        print(f"❌ Ошибка API: {error_type}")
        
        # Выводим дополнительную информацию об ошибке
        if 'invalid-key' in error_type:
            print("  🔑 Ключ API недействителен или просрочен")
        elif 'quota-reached' in error_type:
            print("  📊 Достигнут лимит запросов по тарифу")
        
        return [], project_currencies.copy()
    
    available_rates = api_rates.get('conversion_rates', {})
    print(f"📊 API поддерживает {len(available_rates)} валют")
    
    available = [c for c in project_currencies if c in available_rates]
    missing = [c for c in project_currencies if c not in available_rates]
    
    return available, missing

def main():
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ПОКРЫТИЯ ВАЛЮТ: ExchangeRate-API")
    print("=" * 60)
    
    # Получаем ключ
    api_key = get_api_key()
    print(f"✅ Ключ API получен (первые 8 символов): {api_key[:8]}...")
    
    # Запрашиваем данные
    print("\n📡 Запрос актуальных курсов от USD...")
    data = fetch_latest_rates(api_key, 'USD')
    
    if not data:
        sys.exit(1)
    
    # Анализируем
    available, missing = analyze_coverage(data, CURRENCIES)
    
    # Выводим результаты
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ПОКРЫТИЯ")
    print("=" * 60)
    print(f"Всего валют в проекте: {len(CURRENCIES)}")
    print(f"✅ Доступно в API: {len(available)}")
    print(f"❌ Отсутствует в API: {len(missing)}")
    
    if CURRENCIES:
        coverage = len(available) / len(CURRENCIES) * 100
        print(f"📈 Покрытие: {coverage:.1f}%")
    
    # Проверяем критические валюты
    critical = ['RUB', 'AED', 'KWD', 'SAR', 'QAR', 'UAH', 'KZT']
    critical_missing = [c for c in critical if c in missing]
    if critical_missing:
        print(f"\n⚠️  КРИТИЧЕСКИЕ валюты отсутствуют: {', '.join(critical_missing)}")
    else:
        print(f"\n✅ Все критические валюты доступны!")
    
    if available:
        print(f"\n✅ Первые 5 доступных курсов:")
        for i, currency in enumerate(available[:5], 1):
            rate = data['conversion_rates'].get(currency)
            print(f"  {i}. {currency}: {rate}")
        if len(available) > 5:
            print(f"  ... и еще {len(available) - 5} валют")
    
    if missing:
        print(f"\n❌ Отсутствующие валюты: {', '.join(missing)}")
    
    # Сохраняем результат для отчета
    try:
        report_dir = current_dir / 'data' / 'research_results' / 'exchangerate_api'
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / 'latest_coverage.json'
        
        report = {
            'timestamp': data.get('time_last_update_utc', ''),
            'base_currency': data.get('base_code', 'USD'),
            'project_currencies_total': len(CURRENCIES),
            'available_count': len(available),
            'missing_count': len(missing),
            'coverage_percent': round(coverage, 1) if CURRENCIES else 0,
            'available': available,
            'missing': missing,
            'critical_missing': critical_missing
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Отчет сохранен: {report_file}")
    except Exception as e:
        print(f"\n⚠️  Не удалось сохранить отчет: {e}")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()
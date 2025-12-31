# scripts/research/twelve_data/quick_test.py
"""
Быстрое тестирование покрытия и доступности Twelve Data API.
Запуск из корня проекта: python scripts/research/twelve_data/quick_test.py
"""
import os
import sys
import time
import json
from dotenv import load_dotenv
import requests

# --- Импорт конфигурации проекта из currencies.py ---
# Добавляем корень проекта в sys.path (текущая директория уже корень)
sys.path.insert(0, os.getcwd())

# Импортируем из currencies.py
try:
    from scripts.research.currencies import CURRENCIES, PAIRS
    print(f"✅ Загружено {len(CURRENCIES)} валют и {len(PAIRS)} пар из currencies.py")
except ImportError as e:
    print(f"❌ Ошибка импорта из currencies.py: {e}")
    print("  Убедитесь, что файл scripts/research/currencies.py существует")
    sys.exit(1)

# --- Определение путей относительно корня проекта ---
PROJECT_ROOT = os.getcwd()  # Текущая директория - корень проекта
RESEARCH_RESULTS_DIR = os.path.join(PROJECT_ROOT, "data", "research_results")
TWELVE_DATA_DIR = os.path.join(RESEARCH_RESULTS_DIR, "twelve_data")

# Создаем директории, если их нет
os.makedirs(TWELVE_DATA_DIR, exist_ok=True)

# --- Загрузка ключа API ---
env_path = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(env_path)
API_KEY = os.getenv("TWELVE_DATA_API_KEY")

if not API_KEY:
    print("❌ TWELVE_DATA_API_KEY не найден в .env файле.")
    print(f"   Проверьте файл: {env_path}")
    sys.exit(1)

# --- Константы API ---
BASE_URL = "https://api.twelvedata.com/time_series"

def format_pair_for_api(pair_ticker: str) -> str:
    """
    Преобразует тикер пары из формата проекта ('EURUSD') 
    в формат API Twelve Data ('EUR/USD').
    
    Также обрабатывает пары вида 'USDKWD' -> 'USD/KWD'
    """
    # Убираем возможные пробелы
    pair_ticker = pair_ticker.strip()
    
    # Если уже есть слеш (кто-то уже преобразовал)
    if '/' in pair_ticker:
        return pair_ticker
    
    # Определяем длину валютных кодов
    # Стандартные валюты: 3 буквы (USD, EUR, JPY и т.д.)
    # Определяем где заканчивается первая валюта
    # Пробуем найти стандартные 3-буквенные коды
    if len(pair_ticker) == 6:
        # Самый частый случай: XXXYYY (6 символов)
        return f"{pair_ticker[:3]}/{pair_ticker[3:]}"
    elif len(pair_ticker) == 7:
        # Возможно, это что-то вроде 'USDUAH' где обе по 3?
        # На самом деле это тоже 6, но проверим
        return f"{pair_ticker[:3]}/{pair_ticker[3:]}"
    else:
        # Для нестандартных случаев возвращаем как есть
        print(f"⚠️ Нестандартный формат пары: {pair_ticker}")
        return pair_ticker

def test_single_pair(api_symbol: str, interval: str = "1day", outputsize: int = 5) -> dict:
    """
    Тестирует доступность одной валютной пары через API.
    Возвращает словарь с результатами.
    """
    params = {
        "symbol": api_symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": API_KEY,
        "format": "JSON",
    }
    try:
        response = requests.get(BASE_URL, params=params, timeout=15)
        data = response.json()

        if response.status_code == 200 and data.get("status") == "ok":
            values = data.get("values", [])
            meta = data.get("meta", {})
            
            result = {
                "available": True,
                "api_symbol": api_symbol,
                "data_points": len(values),
                "meta": meta,
            }
            
            if values:
                result["latest_close"] = values[0]["close"]
                result["latest_datetime"] = values[0]["datetime"]
                # Сохраняем 2 первые точки для проверки формата
                result["raw_sample"] = values[:2]
            
            # Логируем дополнительную информацию
            if "currency_base" in meta and "currency_quote" in meta:
                result["base_currency"] = meta["currency_base"]
                result["quote_currency"] = meta["currency_quote"]
                
            return result
        else:
            # API вернул ошибку
            error_msg = data.get("message", f"HTTP {response.status_code}")
            error_code = data.get("code", "unknown")
            
            return {
                "available": False,
                "api_symbol": api_symbol,
                "error": error_msg,
                "code": error_code,
                "response_headers": dict(response.headers),
            }
    except requests.exceptions.Timeout:
        return {"available": False, "api_symbol": api_symbol, "error": "Timeout (15s)"}
    except requests.exceptions.RequestException as e:
        return {"available": False, "api_symbol": api_symbol, "error": f"Request error: {str(e)}"}
    except (KeyError, json.JSONDecodeError) as e:
        return {"available": False, "api_symbol": api_symbol, "error": f"Data parsing error: {e}"}

def main():
    """Основная функция тестирования."""
    print("=" * 60)
    print("🔍 БЫСТРОЕ ТЕСТИРОВАНИЕ TWELVE DATA API")
    print("=" * 60)
    print(f"📁 Корень проекта: {PROJECT_ROOT}")
    print(f"🔑 Ключ API: {API_KEY[:8]}...{API_KEY[-4:] if len(API_KEY) > 12 else '***'}")
    print(f"📊 Всего пар в проекте: {len(PAIRS)}")
    print()

    # 1. Выбираем тестовый набор пар из нашего списка
    # Берем первые 8 пар + добавляем критически важные
    test_pair_tickers = PAIRS[:8]  # Первые 8 пар из списка
    
    # Добавляем критически важные пары, если их еще нет
    critical_pairs = ['USDRUB', 'USDAED', 'USDKWD', 'USDKZT', 'USDUAH']
    for pair in critical_pairs:
        if pair not in test_pair_tickers:
            test_pair_tickers.append(pair)
    
    # Преобразуем в формат API
    test_pairs = [format_pair_for_api(ticker) for ticker in test_pair_tickers]
    
    print(f"🧪 Тестируем {len(test_pairs)} пар:")
    for i, (orig, api_fmt) in enumerate(zip(test_pair_tickers, test_pairs), 1):
        print(f"   {i:2d}. {orig} -> {api_fmt}")
    print()

    # 2. Тестируем каждую пару
    results = {}
    total_to_test = len(test_pairs)
    
    print("📡 Запросы к API...")
    for i, (orig_ticker, api_symbol) in enumerate(zip(test_pair_tickers, test_pairs), 1):
        print(f"  [{i:2d}/{total_to_test:2d}] {orig_ticker} ({api_symbol})...", end="", flush=True)
        
        result = test_single_pair(api_symbol, outputsize=5)
        results[api_symbol] = {
            "original_ticker": orig_ticker,
            **result
        }
        
        if result["available"]:
            close_price = result.get("latest_close", "N/A")
            base = result.get("base_currency", "?")
            quote = result.get("quote_currency", "?")
            print(f" ✅ {base}/{quote}: {close_price}")
        else:
            error = result.get("error", "Unknown error")
            # Укорачиваем длинные ошибки
            if len(error) > 50:
                error = error[:47] + "..."
            print(f" ❌ {error}")
        
        # Соблюдаем лимит: 8 запросов в минуту = 1 запрос каждые 7.5 сек
        # Для быстрого теста ставим 1.5 сек, но для полного теста увеличьте
        if i < total_to_test:
            time.sleep(1.5)

    # 3. Сохраняем результаты
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(TWELVE_DATA_DIR, f"quick_test_{timestamp}.json")
    
    report_data = {
        "project": "AbsCur3",
        "data_source": "Twelve Data",
        "test_timestamp": timestamp,
        "project_root": PROJECT_ROOT,
        "api_key_masked": f"{API_KEY[:4]}...{API_KEY[-4:]}" if len(API_KEY) > 8 else "***",
        "test_config": {
            "total_pairs_in_project": len(PAIRS),
            "pairs_tested": len(test_pairs),
            "outputsize_used": 5,
        },
        "pairs_tested": [
            {
                "original": orig,
                "api_format": api_fmt,
                "available": results[api_fmt]["available"],
                "error": results[api_fmt].get("error") if not results[api_fmt]["available"] else None,
                "data_points": results[api_fmt].get("data_points", 0),
            }
            for orig, api_fmt in zip(test_pair_tickers, test_pairs)
        ],
        "detailed_results": results,
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 Полные результаты сохранены в:\n   {output_file}")
    
    # 4. Формируем сводный отчет
    print("\n" + "=" * 60)
    print("📊 СВОДНЫЙ ОТЧЕТ")
    print("=" * 60)
    
    available_pairs = [api_fmt for api_fmt in results if results[api_fmt]["available"]]
    unavailable_pairs = [api_fmt for api_fmt in results if not results[api_fmt]["available"]]
    
    print(f"✅ Доступно: {len(available_pairs)}/{len(test_pairs)} пар")
    print(f"❌ Недоступно: {len(unavailable_pairs)}/{len(test_pairs)} пар")
    
    if available_pairs:
        print("\n📈 Пример данных (первая доступная пара):")
        first_available = available_pairs[0]
        first_result = results[first_available]
        
        print(f"   Пара: {first_result['original_ticker']} ({first_available})")
        print(f"   Точек данных: {first_result.get('data_points', 0)}")
        print(f"   Последняя цена: {first_result.get('latest_close', 'N/A')}")
        print(f"   Дата: {first_result.get('latest_datetime', 'N/A')}")
        
        if 'meta' in first_result:
            meta = first_result['meta']
            print(f"   Интервал: {meta.get('interval', 'N/A')}")
            print(f"   Символ: {meta.get('symbol', 'N/A')}")
            print(f"   Обмен: {meta.get('exchange', 'N/A')}")
    
    if unavailable_pairs:
        print(f"\n⚠️ Проблемные пары ({len(unavailable_pairs)}):")
        for api_fmt in unavailable_pairs:
            orig = results[api_fmt]["original_ticker"]
            error = results[api_fmt].get("error", "No error message")
            print(f"   • {orig} ({api_fmt}): {error[:60]}...")
    
    # 5. Рекомендации по следующим шагам
    print("\n" + "=" * 60)
    print("🎯 СЛЕДУЮЩИЕ ШАГИ")
    print("=" * 60)
    
    if len(available_pairs) >= len(test_pairs) * 0.8:  # 80% доступно
        print("1. 📅 Протестируйте глубину истории: увеличьте outputsize до 5000")
        print("2. 🔄 Проверьте лимиты: протестируйте 85 запросов подряд")
        print("3. 🗂️ Создайте скрипт полного покрытия для всех 85 пар")
    else:
        print("1. 🔍 Проверьте формат пар: возможно, нужно адаптировать format_pair_for_api()")
        print("2. 📖 Изучите документацию Twelve Data по доступным парам")
        print("3. ⚠️ Рассмотрите другие источники для недостающих пар")
    
    print(f"\n🚀 Для полного теста создайте: scripts/research/twelve_data/test_full_coverage.py")

if __name__ == "__main__":
    main()
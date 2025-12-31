# scripts/research/twelve_data/test_history_depth.py
"""
Тестирование глубины исторических данных Twelve Data API.
Запуск из корня проекта: python scripts/research/twelve_data/test_history_depth.py
"""
import os
import sys
import time
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

# --- Импорт конфигурации проекта ---
sys.path.insert(0, os.getcwd())
try:
    from scripts.research.currencies import PAIRS
    print(f"✅ Загружено {len(PAIRS)} пар из currencies.py")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

# --- Конфигурация ---
PROJECT_ROOT = os.getcwd()
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
API_KEY = os.getenv("TWELVE_DATA_API_KEY")

if not API_KEY:
    print("❌ Ключ API не найден.")
    sys.exit(1)

BASE_URL = "https://api.twelvedata.com/time_series"
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "research_results", "twelve_data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def format_pair_for_api(pair_ticker: str) -> str:
    """Преобразует формат пары из 'EURUSD' в 'EUR/USD'."""
    if len(pair_ticker) == 6:
        return f"{pair_ticker[:3]}/{pair_ticker[3:]}"
    return pair_ticker

def test_historical_depth(api_symbol: str, interval: str = "1day", max_outputsize: int = 5000) -> dict:
    """
    Тестирует, сколько исторических данных можно получить за один запрос.
    Согласно документации, максимальный outputsize = 5000[citation:3].
    """
    print(f"\n📊 Тестируем пару: {api_symbol}")
    
    test_cases = [
        {"outputsize": 10, "desc": "Короткий запрос (10 точек)"},
        {"outputsize": 100, "desc": "Средний запрос (100 точек)"},
        {"outputsize": max_outputsize, "desc": f"Максимальный запрос ({max_outputsize} точек)"},
    ]

    results = {}
    for case in test_cases:
        print(f"  Запрос: {case['desc']}...", end="", flush=True)
        params = {
            "symbol": api_symbol,
            "interval": interval,
            "outputsize": case['outputsize'],
            "apikey": API_KEY,
            "format": "JSON",
        }

        try:
            response = requests.get(BASE_URL, params=params, timeout=30)
            data = response.json()
            
            if response.status_code == 200 and data.get("status") == "ok":
                values = data.get("values", [])
                meta = data.get("meta", {})
                
                # Определяем даты начала и конца периода
                earliest_date = values[-1]['datetime'] if values else None
                latest_date = values[0]['datetime'] if values else None
                
                # Подсчитываем примерное количество дней
                day_count = "N/A"
                if earliest_date and latest_date:
                    try:
                        date_format = "%Y-%m-%d" if len(earliest_date) == 10 else "%Y-%m-%d %H:%M:%S"
                        start = datetime.strptime(earliest_date, date_format)
                        end = datetime.strptime(latest_date, date_format)
                        day_count = (end - start).days
                    except ValueError:
                        pass
                
                result = {
                    "success": True,
                    "requested_points": case['outputsize'],
                    "received_points": len(values),
                    "earliest_date": earliest_date,
                    "latest_date": latest_date,
                    "approx_days_covered": day_count,
                    "meta_symbol": meta.get("symbol"),
                    "meta_interval": meta.get("interval"),
                }
                print(f" ✅ Получено {len(values)} точек. Период: ~{day_count} дней.")
                
            else:
                result = {
                    "success": False,
                    "error": data.get("message", f"HTTP {response.status_code}"),
                }
                print(f" ❌ Ошибка: {result['error'][:50]}...")
                
        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
            }
            print(f" ❌ Исключение: {e}")
        
        results[case['outputsize']] = result
        time.sleep(8)  # Строго соблюдаем лимит 8 запросов в минуту
    
    return results

def main():
    print("=" * 70)
    print("🔍 ТЕСТИРОВАНИЕ ГЛУБИНЫ ИСТОРИЧЕСКИХ ДАННЫХ TWELVE DATA")
    print("=" * 70)
    print(f"📌 Важно: Максимум 5000 точек данных за один запрос[citation:3]")
    print(f"📌 Ключ API: {API_KEY[:8]}...{API_KEY[-4:] if len(API_KEY) > 12 else '***'}")
    print()

    # Выбираем тестовые пары: EUR/USD для надежности + проблемная пара из быстрого теста
    test_pair_tickers = ['EURUSD', 'USDRUB']  # USDRUB не сработал ранее из-за лимитов
    test_pairs = [format_pair_for_api(ticker) for ticker in test_pair_tickers]

    all_results = {}
    for pair in test_pairs:
        # Даем системе "перевести дыхание" между парами
        time.sleep(10)
        all_results[pair] = test_historical_depth(pair)

    # Сохранение полных результатов
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"history_depth_test_{timestamp}.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "test_timestamp": timestamp,
            "api_note": "Максимальный outputsize ограничен 5000 точками данных за запрос[citation:3]",
            "tested_pairs": test_pairs,
            "results": all_results,
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Полные результаты сохранены:\n   {output_file}")

    # Анализ и вывод сводки
    print("\n" + "=" * 70)
    print("📋 СВОДКА ДЛЯ ПРИНЯТИЯ РЕШЕНИЙ ПО AbsCur3")
    print("=" * 70)
    
    for pair in test_pairs:
        print(f"\n📈 Пара: {pair}")
        res = all_results[pair]
        
        max_result = res.get(5000)  # Смотрим результат максимального запроса
        if max_result and max_result.get("success"):
            pts = max_result["received_points"]
            days = max_result["approx_days_covered"]
            earliest = max_result["earliest_date"]
            
            print(f"   ✅ Макс. точек за запрос: {pts} (~{days} дней)")
            print(f"   📅 Самая ранняя дата в ответе: {earliest}")
            
            # Оценка пригодности для проекта (20+ лет ≈ 5000+ торговых дней)
            if days != "N/A":
                if days >= 5000:
                    print("   🎯 ВЫВОД: Потенциально достаточно для >20 лет истории.")
                elif days >= 1000:
                    print(f"   ⚠️  ВЫВОД: ~{days//365} лет. Нужно несколько запросов (по 5000 точек).")
                else:
                    print(f"   ❌ ВЫВОД: Только ~{days} дней. Не подходит как основной источник глубокой истории.")
        else:
            print(f"   ❌ Максимальный запрос не удался.")
            if max_result:
                print(f"      Ошибка: {max_result.get('error')}")

    print("\n" + "=" * 70)
    print("🎯 РЕКОМЕНДУЕМЫЕ СЛЕДУЮЩИЕ ШАГИ")
    print("=" * 70)
    print("1. Проанализируйте дату начала данных для EUR/USD.")
    print("2. Если данных <5000 дней, проверьте endpoint '/earliest_timestamp'[citation:1] для точной даты.")
    print("3. Рассчитайте, сколько запросов по 5000 точек нужно для 20 лет (~5000 дней).")
    print("4. Оцените стратегию: несколько запросов с start_date/end_date[citation:3] vs. другие источники.")

if __name__ == "__main__":
    main()
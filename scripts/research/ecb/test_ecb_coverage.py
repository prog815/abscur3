"""
test_ecb_coverage.py
Скрипт для проверки покрытия валют проекта в данных Европейского центрального банка (ECB).
Проверяет доступность исторических данных для каждой валюты из списка проекта.
"""

import sys
import requests
import time
import json
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime
import xml.etree.ElementTree as ET

# --- Ручной импорт конфигурации валют ---
# Поскольку скрипт находится в scripts/research/ecb/, currencies.py на уровень выше
PROJECT_ROOT = Path(__file__).parent.parent.parent
CURRENCIES_PATH = PROJECT_ROOT / "scripts" / "research" / "currencies.py"
CURRENCIES_PATH = Path(__file__).parent.parent / "currencies.py"

if not CURRENCIES_PATH.exists():
    print(f"Ошибка: Файл currencies.py не найден по пути: {CURRENCIES_PATH}")
    print("Создайте файл currencies.py или укажите правильный путь.")
    sys.exit(1)

# Ручной импорт конфигурации
CURRENCIES = []
CURRENCY_NAMES = {}
PAIRS = []

try:
    # Читаем и выполняем файл конфигурации
    with open(CURRENCIES_PATH, 'r', encoding='utf-8') as f:
        config_content = f.read()
    
    # Создаем временное пространство имен для выполнения
    config_globals = {}
    exec(config_content, config_globals)
    
    # Извлекаем необходимые переменные
    CURRENCIES = config_globals.get('CURRENCIES', [])
    CURRENCY_NAMES = config_globals.get('CURRENCY_NAMES', {})
    PAIRS = config_globals.get('PAIRS', [])
    
    if not CURRENCIES:
        print("Предупреждение: CURRENCIES пуст. Используем тестовый список.")
        # Тестовый список на случай отсутствия конфигурации
        CURRENCIES = ['USD', 'EUR', 'JPY', 'GBP', 'CHF', 'CAD', 'AUD', 'NZD', 'CNY', 'HKD', 'SGD', 
                      'RUB', 'AED', 'ARS', 'BRL', 'CLP', 'COP', 'CZK', 'DKK', 'EGP', 'HUF', 'IDR', 
                      'ILS', 'INR', 'ISK', 'KRW', 'KWD', 'KZT', 'MXN', 'MYR', 'NOK', 'PEN', 'PHP', 
                      'PKR', 'PLN', 'QAR', 'RON', 'SAR', 'SEK', 'THB', 'TRY', 'TWD', 'UAH', 'VND', 'ZAR']
        
except Exception as e:
    print(f"Ошибка загрузки конфигурации: {e}")
    print("Используем тестовый список валют.")
    CURRENCIES = ['USD', 'EUR', 'JPY', 'GBP', 'CHF', 'CAD', 'AUD', 'NZD', 'CNY', 'HKD', 'SGD', 
                  'RUB', 'AED', 'ARS', 'BRL', 'CLP', 'COP', 'CZK', 'DKK', 'EGP', 'HUF', 'IDR', 
                  'ILS', 'INR', 'ISK', 'KRW', 'KWD', 'KZT', 'MXN', 'MYR', 'NOK', 'PEN', 'PHP', 
                  'PKR', 'PLN', 'QAR', 'RON', 'SAR', 'SEK', 'THB', 'TRY', 'TWD', 'UAH', 'VND', 'ZAR']

# --- Конфигурация ECB API ---
ECB_API_BASE_URL = "https://data-api.ecb.europa.eu/service/data/EXR"
ECB_REQUEST_DELAY = 0.5  # Задержка между запросами (сек)

# Валюты, требующие особого внимания
SPECIAL_CURRENCIES = ["RUB", "AED", "KWD", "SAR", "QAR", "UAH", "KZT", "ARS", "CLP", "COP", "PEN"]

class ECBCoverageTester:
    """Класс для тестирования покрытия валют в данных ECB."""

    def __init__(self, currencies: List[str]):
        self.currencies = currencies
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "AbsCur3-Research/1.0"
        })
        self.results = {}
        
        # Убираем EUR из тестируемых валют (это базовая валюта ECB)
        if 'EUR' in self.currencies:
            self.currencies.remove('EUR')
            print("EUR исключен из тестирования (базовая валюта ECB)")

    def test_single_currency(self, currency: str) -> Tuple[bool, str]:
        """Проверяет доступность данных для валюты в ECB через XML источник."""
        # Используем простой XML источник вместо SDMX API
        xml_url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
        
        try:
            response = self.session.get(xml_url, timeout=10)
            response.raise_for_status()
            
            # Парсим XML
            import xml.etree.ElementTree as ET
            
            # Определяем namespace
            namespaces = {
                'gesmes': 'http://www.gesmes.org/xml/2002-08-01',
                '': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'
            }
            
            root = ET.fromstring(response.content)
            
            # Ищем все элементы Cube с атрибутом currency
            for cube in root.findall('.//{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube[@currency]', namespaces):
                if cube.get('currency') == currency:
                    rate = cube.get('rate')
                    return True, f"Данные доступны (курс: {rate})"
            
            # Если не нашли в daily, пробуем исторический файл (90 дней)
            return self._check_historical_xml(currency)
                
        except requests.exceptions.Timeout:
            return False, "Таймаут запроса"
        except Exception as e:
            return False, f"Ошибка при обработке XML: {e}"

    def _check_historical_xml(self, currency: str) -> Tuple[bool, str]:
        """Проверяет валюту в историческом XML файле (90 дней)."""
        try:
            xml_url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
            response = self.session.get(xml_url, timeout=10)
            response.raise_for_status()
            
            import xml.etree.ElementTree as ET
            namespaces = {
                'gesmes': 'http://www.gesmes.org/xml/2002-08-01',
                '': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'
            }
            
            root = ET.fromstring(response.content)
            
            # Ищем валюту в любом из исторических данных
            for cube in root.findall('.//{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube[@currency]', namespaces):
                if cube.get('currency') == currency:
                    return True, "Данные доступны в исторических файлах"
            
            return False, "Валюта не найдена в данных ECB"
            
        except Exception as e:
            return False, f"Ошибка проверки исторических данных: {e}"

    def test_all_currencies(self) -> Dict[str, Dict]:
        """Тестирует все валюты из списка."""
        print(f"Начинаем тестирование покрытия ECB для {len(self.currencies)} валют...")
        print("-" * 60)
        
        for i, currency in enumerate(self.currencies, 1):
            print(f"[{i}/{len(self.currencies)}] Тестируем {currency} ({CURRENCY_NAMES.get(currency, 'Нет описания')})...", end=" ", flush=True)
            
            is_available, message = self.test_single_currency(currency)
            
            self.results[currency] = {
                "available": is_available,
                "message": message,
                "name": CURRENCY_NAMES.get(currency, "Неизвестно")
            }
            
            status = "✅ ДОСТУПНА" if is_available else "❌ НЕДОСТУПНА"
            print(f"{status} ({message})")
        
        return self.results

    def analyze_coverage(self) -> Dict:
        """Анализирует результаты тестирования."""
        available = [c for c, r in self.results.items() if r["available"]]
        unavailable = [c for c, r in self.results.items() if not r["available"]]
        
        special_available = [c for c in SPECIAL_CURRENCIES if c in available]
        special_unavailable = [c for c in SPECIAL_CURRENCIES if c in unavailable]
        
        total_tested = len(self.results)
        coverage_percentage = round(len(available) / total_tested * 100, 1) if total_tested > 0 else 0
        
        analysis = {
            "total_tested": total_tested,
            "available_count": len(available),
            "unavailable_count": len(unavailable),
            "coverage_percentage": coverage_percentage,
            "available_currencies": available,
            "unavailable_currencies": unavailable,
            "special_currencies": {
                "tested": SPECIAL_CURRENCIES,
                "available": special_available,
                "unavailable": special_unavailable
            }
        }
        
        return analysis

    def save_results(self, analysis: Dict):
        """Сохраняет результаты тестирования в файлы."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("data/research_results/ecb")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Полный отчёт в JSON
        full_report = {
            "test_date": datetime.now().isoformat(),
            "project_currencies_count": len(CURRENCIES),
            "tested_currencies_count": len(self.results),
            "results": self.results,
            "analysis": analysis
        }
        
        report_path = output_dir / f"coverage_report_{timestamp}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(full_report, f, ensure_ascii=False, indent=2)
        
        # 2. Текстовый отчёт
        text_report = f"""Отчёт о покрытии валют ECB
Дата тестирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Проект: AbsCur3

ОБЩАЯ СТАТИСТИКА:
-----------------
Всего валют в проекте: {len(CURRENCIES)}
Протестировано валют: {analysis['total_tested']}
Доступно в ECB: {analysis['available_count']}
Недоступно в ECB: {analysis['unavailable_count']}
Покрытие: {analysis['coverage_percentage']}%

ДОСТУПНЫЕ ВАЛЮТЫ ({analysis['available_count']}):
-------------------------
{', '.join(sorted(analysis['available_currencies']))}

НЕДОСТУПНЫЕ ВАЛЮТЫ ({analysis['unavailable_count']}):
---------------------------
{', '.join(sorted(analysis['unavailable_currencies']))}

ОСОБЫЕ ВАЛЮТЫ (проблемные для проекта):
---------------------------------------
Доступны: {', '.join(analysis['special_currencies']['available']) or 'Нет'}
Недоступны: {', '.join(analysis['special_currencies']['unavailable']) or 'Нет'}

ПОДРОБНЫЕ РЕЗУЛЬТАТЫ ПО ВАЛЮТАМ:
--------------------------------
"""
        for currency, result in sorted(self.results.items()):
            status = "✅" if result["available"] else "❌"
            text_report += f"{status} {currency}: {result['name']}\n"
            text_report += f"   Статус: {result['message']}\n"
        
        text_report_path = output_dir / f"coverage_summary_{timestamp}.txt"
        with open(text_report_path, 'w', encoding='utf-8') as f:
            f.write(text_report)
        
        # 3. Списки валют
        available_path = output_dir / f"available_currencies_{timestamp}.txt"
        with open(available_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(sorted(analysis['available_currencies'])))
        
        unavailable_path = output_dir / f"unavailable_currencies_{timestamp}.txt"
        with open(unavailable_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(sorted(analysis['unavailable_currencies'])))
        
        print(f"\n{'='*60}")
        print("Результаты сохранены:")
        print(f"  Полный отчёт: {report_path}")
        print(f"  Текст. отчёт: {text_report_path}")

def main():
    """Основная функция запуска тестирования."""
    print("=" * 60)
    print("ECB COVERAGE TESTER для проекта AbsCur3")
    print("=" * 60)
    
    tester = ECBCoverageTester(CURRENCIES)
    results = tester.test_all_currencies()
    
    analysis = tester.analyze_coverage()
    
    print(f"\n{'='*60}")
    print("СВОДКА ПОКРЫТИЯ ECB:")
    print(f"  Доступно валют: {analysis['available_count']}/{analysis['total_tested']} ({analysis['coverage_percentage']}%)")
    print(f"  Критические валюты:")
    
    for currency in SPECIAL_CURRENCIES:
        if currency in results:
            status = "✅" if results[currency]["available"] else "❌"
            print(f"    {status} {currency}: {results[currency]['message']}")
    
    tester.save_results(analysis)
    
    print(f"\n{'='*60}")
    print("РЕКОМЕНДАЦИИ ДЛЯ ПРОЕКТА ABScur3:")
    
    if analysis['coverage_percentage'] > 70:
        print("  ✅ ECB может быть основным источником для EUR-пар")
    else:
        print("  ⚠️  Покрытие ECB ограничено, требуется дополнение другими источниками")
    
    if "RUB" in analysis['unavailable_currencies']:
        print("  ⚠️  RUB недоступен в ECB (приостановлен с 2022) - требуется Finam/ЦБ РФ")
    
    gcc_currencies = ["AED", "KWD", "SAR", "QAR"]
    missing_gcc = [c for c in gcc_currencies if c in analysis['unavailable_currencies']]
    if missing_gcc:
        print(f"  ⚠️  Валюты GCC {missing_gcc} недоступны - требуется Twelve Data/EODHD")
    
    print(f"\nСледующий шаг: Запустить test_historical_depth.py для проверки глубины истории")

if __name__ == "__main__":
    main()
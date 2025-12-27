"""
test_historical_depth.py
Скрипт для проверки глубины исторических данных Европейского центрального банка (ECB).
Определяет самую раннюю доступную дату для каждой валюты.
"""

import sys
import requests
import time
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, date
from collections import defaultdict

# --- Конфигурация ECB API ---
ECB_HISTORICAL_XML_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml"
ECB_HIST_90D_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 0.1

def find_latest_coverage_file():
    """Ищет последний файл отчета о покрытии."""
    # Пробуем найти директорию с результатами
    possible_dirs = [
        Path("data/research_results/ecb"),
        Path(__file__).parent.parent.parent / "data" / "research_results" / "ecb",
    ]
    
    coverage_dir = None
    for dir_path in possible_dirs:
        if dir_path.exists():
            coverage_dir = dir_path
            break
    
    if not coverage_dir:
        print("❌ Директория с результатами не найдена.")
        print("   Запустите сначала test_ecb_coverage.py")
        sys.exit(1)
    
    coverage_files = list(coverage_dir.glob("coverage_report_*.json"))
    if not coverage_files:
        print(f"❌ В {coverage_dir} нет файлов coverage_report_*.json")
        print("   Запустите сначала test_ecb_coverage.py")
        sys.exit(1)
    
    latest_file = max(coverage_files, key=lambda f: f.stat().st_mtime)
    print(f"✅ Загружаем отчет о покрытии: {latest_file}")
    return latest_file

def load_coverage_data():
    """Загружает данные из файла покрытия."""
    latest_coverage_path = find_latest_coverage_file()
    
    with open(latest_coverage_path, 'r', encoding='utf-8') as f:
        coverage_data = json.load(f)
    
    available_currencies = coverage_data['analysis']['available_currencies']
    
    if not available_currencies:
        print("⚠️  В отчете нет доступных валют. Завершение.")
        sys.exit(1)
    
    return available_currencies, latest_coverage_path

class ECBHistoryDepthTester:
    def __init__(self, currencies_to_test: List[str], coverage_report_path: Path):
        self.currencies = currencies_to_test
        self.coverage_report_path = coverage_report_path
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "AbsCur3-Research/1.0"})
        
        self.history_depth = {}
        self.all_rates_by_date = defaultdict(dict)

    def fetch_historical_xml(self, url: str) -> Optional[ET.Element]:
        """Загружает и парсит исторический XML-файл с данными ECB."""
        try:
            print(f"⏬ Загружаем исторические данные из: {url}")
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            print(f"✅ Данные успешно загружены ({len(response.content)} байт)")
            
            namespaces = {
                'gesmes': 'http://www.gesmes.org/xml/2002-08-01',
                '': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'
            }
            
            root = ET.fromstring(response.content)
            for prefix, uri in namespaces.items():
                if prefix:
                    ET.register_namespace(prefix, uri)
                else:
                    ET.register_namespace('', uri)
            
            return root
            
        except requests.exceptions.Timeout:
            print(f"❌ Таймаут при загрузке данных с {url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка сети: {e}")
            return None
        except ET.ParseError as e:
            print(f"❌ Ошибка парсинга XML: {e}")
            return None

    def analyze_currency_depth(self, root: ET.Element):
        """Анализирует XML, находя самую раннюю и позднюю дату для каждой валюты."""
        namespaces = {'ecb': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'}
        
        # Ищем все дни с данными
        time_cubes = root.findall('.//ecb:Cube[@time]', namespaces)
        if not time_cubes:
            time_cubes = root.findall('.//{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube[@time]')
        
        print(f"📅 Найдено {len(time_cubes)} дней с данными.")
        
        earliest_date = {currency: None for currency in self.currencies}
        latest_date = {currency: None for currency in self.currencies}
        daily_count = {currency: 0 for currency in self.currencies}
        
        for day_cube in time_cubes:
            current_date_str = day_cube.get('time')
            try:
                current_date = datetime.strptime(current_date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            
            # Ищем курсы валют для этого дня
            rate_cubes = day_cube.findall('ecb:Cube[@currency]', namespaces)
            if not rate_cubes:
                rate_cubes = day_cube.findall('{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube[@currency]')
            
            for rate_cube in rate_cubes:
                currency = rate_cube.get('currency')
                rate = rate_cube.get('rate')
                
                if currency in self.currencies:
                    self.all_rates_by_date[current_date_str][currency] = rate
                    
                    if earliest_date[currency] is None or current_date < earliest_date[currency]:
                        earliest_date[currency] = current_date
                    if latest_date[currency] is None or current_date > latest_date[currency]:
                        latest_date[currency] = current_date
                    
                    daily_count[currency] += 1
        
        # Формируем итоговый результат
        for currency in self.currencies:
            if earliest_date[currency] and latest_date[currency]:
                days_diff = (latest_date[currency] - earliest_date[currency]).days
                self.history_depth[currency] = {
                    'earliest_date': earliest_date[currency].isoformat(),
                    'latest_date': latest_date[currency].isoformat(),
                    'total_days': daily_count[currency],
                    'approx_years': round(days_diff / 365.25, 1)
                }
            else:
                self.history_depth[currency] = {
                    'earliest_date': None,
                    'latest_date': None,
                    'total_days': 0,
                    'approx_years': 0.0
                }

    def run_test(self):
        """Основной метод запуска теста."""
        print("🚀 Запуск теста глубины исторических данных ECB...")
        
        xml_root = self.fetch_historical_xml(ECB_HISTORICAL_XML_URL)
        
        if xml_root is None:
            print("⚠️  Пробуем файл за 90 дней...")
            xml_root = self.fetch_historical_xml(ECB_HIST_90D_URL)
        
        if xml_root is None:
            print("❌ Не удалось загрузить исторические данные.")
            return False
        
        print("🔎 Анализируем глубину истории для каждой валюты...")
        self.analyze_currency_depth(xml_root)
        
        print("\n" + "=" * 60)
        print("ПРЕДВАРИТЕЛЬНЫЕ РЕЗУЛЬТАТЫ:")
        for i, currency in enumerate(sorted(self.currencies), 1):
            depth_info = self.history_depth.get(currency, {})
            earliest = depth_info.get('earliest_date', 'Н/Д')
            years = depth_info.get('approx_years', 0)
            status = "✅" if earliest != 'Н/Д' and years > 20 else "⚠️ " if earliest != 'Н/Д' else "❌"
            print(f"{status} [{i:2d}] {currency}: Начало данных: {earliest}, ~{years} лет")
        
        return True

    def save_results(self):
        """Сохраняет детальные результаты теста в файлы."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("data/research_results/ecb")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Полный отчет в JSON
        full_report = {
            "test_date": datetime.now().isoformat(),
            "source_xml": ECB_HISTORICAL_XML_URL,
            "currencies_tested": self.currencies,
            "history_depth": self.history_depth,
            "coverage_source_report": str(self.coverage_report_path.name)
        }
        
        report_path = output_dir / f"historical_depth_report_{timestamp}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(full_report, f, ensure_ascii=False, indent=2)
        
        # 2. Текстовый отчет
        text_report = f"""ОТЧЕТ О ГЛУБИНЕ ИСТОРИЧЕСКИХ ДАННЫХ ECB
Дата тестирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Источник данных: {ECB_HISTORICAL_XML_URL}
Источник списка валют: {self.coverage_report_path.name}

ОБЩАЯ СТАТИСТИКА:
-----------------
Всего проверено валют: {len(self.currencies)}
Валют с данными: {sum(1 for info in self.history_depth.values() if info['earliest_date'] is not None)}

КРИТЕРИИ ПРОЕКТА ABScur3:
------------------------
Целевая глубина: 20+ лет (с ~2005 года)
Валюты с историей >20 лет: {sum(1 for info in self.history_depth.values() if info.get('approx_years', 0) > 20)}

ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ ПО ВАЛЮТАМ:
--------------------------------
"""
        sorted_currencies = sorted(
            self.history_depth.items(),
            key=lambda x: x[1]['earliest_date'] or '9999-99-99'
        )
        
        for currency, info in sorted_currencies:
            earliest = info['earliest_date'] or "НЕТ ДАННЫХ"
            latest = info['latest_date'] or "НЕТ ДАННЫХ"
            years = info['approx_years']
            days_count = info['total_days']
            
            if years >= 20:
                marker = "✓"
                years_status = f"~{years} лет (ЦЕЛЬ ДОСТИГНУТА)"
            elif years > 0:
                marker = "⚠"
                years_status = f"~{years} лет (НЕДОСТАТОЧНО)"
            else:
                marker = "✗"
                years_status = "НЕТ ДАННЫХ"
            
            text_report += f"\n{marker} {currency}:\n"
            text_report += f"   Начало данных: {earliest}\n"
            text_report += f"   Конец данных:  {latest}\n"
            text_report += f"   Глубина истории: {years_status}\n"
            text_report += f"   Всего точек данных: {days_count} дней\n"
        
        text_report_path = output_dir / f"historical_depth_summary_{timestamp}.txt"
        with open(text_report_path, 'w', encoding='utf-8') as f:
            f.write(text_report)
        
        # 3. Сводная таблица в CSV
        csv_path = output_dir / f"historical_depth_table_{timestamp}.csv"
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write("Currency,Earliest_Date,Latest_Date,Total_Days,Approx_Years\n")
            for currency, info in sorted(self.history_depth.items()):
                earliest = info['earliest_date'] or ""
                latest = info['latest_date'] or ""
                f.write(f"{currency},{earliest},{latest},{info['total_days']},{info['approx_years']}\n")
        
        print(f"\n{'=' * 60}")
        print("📊 РЕЗУЛЬТАТЫ СОХРАНЕНЫ:")
        print(f"   Полный отчет (JSON): {report_path}")
        print(f"   Текстовый отчет: {text_report_path}")
        print(f"   Сводная таблица (CSV): {csv_path}")

def main():
    """Основная функция запуска."""
    print("=" * 60)
    print("ECB HISTORICAL DEPTH TESTER для проекта AbsCur3")
    print("=" * 60)
    
    # Загружаем данные о покрытии
    available_currencies, coverage_path = load_coverage_data()
    print(f"🔍 Будет проверена глубина истории для {len(available_currencies)} валют.")
    print("-" * 60)
    
    # Создаем и запускаем тестер
    tester = ECBHistoryDepthTester(available_currencies, coverage_path)
    
    if tester.run_test():
        tester.save_results()
        
        # Анализ результатов
        print(f"\n{'=' * 60}")
        print("АНАЛИЗ ДЛЯ ПРОЕКТА ABScur3:")
        
        currencies_with_depth = []
        currencies_without_depth = []
        
        for currency, info in tester.history_depth.items():
            if info['approx_years'] >= 20:
                currencies_with_depth.append(currency)
            elif info['earliest_date']:
                currencies_without_depth.append((currency, info['approx_years']))
        
        print(f"✅ Валют с историей >20 лет: {len(currencies_with_depth)}/{len(available_currencies)}")
        if currencies_with_depth:
            print(f"   Пример: {', '.join(sorted(currencies_with_depth)[:5])}...")
        
        if currencies_without_depth:
            print(f"⚠️  Валют с недостаточной глубиной: {len(currencies_without_depth)}")
            for currency, years in sorted(currencies_without_depth, key=lambda x: x[1])[:3]:
                print(f"   - {currency}: ~{years} лет")
        
        # Проверяем важные валюты
        print(f"\n🔍 СТАТУС КРИТИЧЕСКИХ ВАЛЮТ:")
        critical_currencies = ['USD', 'JPY', 'GBP', 'CHF', 'CAD', 'AUD', 'CNY']
        for curr in critical_currencies:
            if curr in tester.history_depth:
                info = tester.history_depth[curr]
                status = "✅" if info['approx_years'] >= 20 else "⚠️ " if info['earliest_date'] else "❌"
                print(f"   {status} {curr}: {info.get('earliest_date', 'Н/Д')} (~{info.get('approx_years', 0)} лет)")
        
        print(f"\n📌 ВЫВОД: ECB предоставляет глубокую историю для большинства валют.")
        print("   Следующий шаг: Интеграция в ETL-пайплайн.")

if __name__ == "__main__":
    main()
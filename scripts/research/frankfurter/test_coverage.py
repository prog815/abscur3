#!/usr/bin/env python3
"""
Устойчивое тестирование Frankfurter.app с обработкой таймаутов и ограничений
"""

import requests
import json
import time
import sys
from datetime import datetime
from pathlib import Path
import logging
from typing import Dict, List, Optional
import random

sys.path.append(str(Path(__file__).parent.parent))
from currencies import CURRENCIES, CURRENCY_NAMES, PAIRS

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Конфигурация
PROJECT_ROOT = Path(__file__).parents[3]
RESULTS_DIR = PROJECT_ROOT / "data" / "research_results" / "frankfurter"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

FRANKFURTER_BASE_URL = "https://api.frankfurter.app"
TEST_DATE = "2024-01-02"


class RobustFrankfurterTester:
    """Устойчивый тестер с обработкой ошибок"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Более щадящие настройки
        self.timeout = 30  # Увеличиваем таймаут
        self.max_retries = 5  # Больше попыток
        self.base_delay = 1.0  # Базовая задержка
        self.max_delay = 10.0  # Максимальная задержка
        
        self.results = {
            "test_date": datetime.now().isoformat(),
            "currency_coverage": {},
            "pair_coverage": {},
            "errors": []
        }
    
    def safe_request(self, url: str, description: str = "") -> Optional[Dict]:
        """Безопасный запрос с экспоненциальной задержкой"""
        for attempt in range(self.max_retries):
            try:
                # Случайная задержка для избежания блокировки
                delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                delay = min(delay, self.max_delay)
                time.sleep(delay)
                
                logger.debug(f"Попытка {attempt+1}/{self.max_retries}: {description}")
                
                response = self.session.get(url, timeout=self.timeout)
                
                if response.status_code == 429:  # Too Many Requests
                    wait_time = int(response.headers.get('Retry-After', 30))
                    logger.warning(f"Слишком много запросов. Ждем {wait_time} секунд")
                    time.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.Timeout as e:
                logger.warning(f"Таймаут попытки {attempt+1}: {description}")
                if attempt == self.max_retries - 1:
                    self.results["errors"].append(f"Таймаут: {description}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Ошибка запроса {attempt+1}: {e}")
                if attempt == self.max_retries - 1:
                    self.results["errors"].append(f"Ошибка запроса: {description} - {e}")
                    return None
        
        return None
    
    def test_currency_batch(self, currencies: List[str]) -> Dict:
        """Тестирует валюты батчами для снижения нагрузки"""
        logger.info(f"🔍 Тестирование {len(currencies)} валют...")
        
        available = []
        unavailable = []
        
        # Используем batch запрос для нескольких валют сразу
        currencies_to_test = [c for c in currencies if c != "EUR"]
        
        # Разбиваем на батчи по 5 валют
        batch_size = 5
        for i in range(0, len(currencies_to_test), batch_size):
            batch = currencies_to_test[i:i+batch_size]
            batch_str = ",".join(batch)
            
            url = f"{FRANKFURTER_BASE_URL}/{TEST_DATE}?from=EUR&to={batch_str}"
            
            data = self.safe_request(url, f"Батч {i//batch_size + 1}: {batch_str}")
            
            if data and 'rates' in data:
                rates = data['rates']
                for currency in batch:
                    if currency in rates:
                        available.append(currency)
                        logger.info(f"✅ {currency}: {rates[currency]:.4f}")
                    else:
                        unavailable.append(currency)
                        logger.warning(f"❌ {currency}: не найдена в ответе")
            else:
                # Если batch запрос не сработал, пробуем по одной
                for currency in batch:
                    if self.test_single_currency(currency):
                        available.append(currency)
                    else:
                        unavailable.append(currency)
            
            # Дополнительная пауза между батчами
            time.sleep(2)
        
        # EUR всегда доступен
        if "EUR" in currencies:
            available.append("EUR")
        
        return {
            "available": available,
            "unavailable": unavailable,
            "total": len(currencies),
            "coverage": len(available) / len(currencies) * 100
        }
    
    def test_single_currency(self, currency: str) -> bool:
        """Тестирует одну валюту"""
        if currency == "EUR":
            return True
            
        url = f"{FRANKFURTER_BASE_URL}/{TEST_DATE}?from=EUR&to={currency}"
        data = self.safe_request(url, f"Валюта {currency}")
        
        if data and currency in data.get('rates', {}):
            return True
        return False
    
    def test_critical_currencies(self) -> Dict:
        """Тестирует только критические валюты для быстрой оценки"""
        critical_currencies = [
            "USD", "EUR", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD",  # Основные
            "RUB", "CNY", "HKD", "SGD",  # Важные для проекта
            "AED", "KWD", "UAH", "KZT"   # Проблемные (для проверки)
        ]
        
        logger.info("🎯 Тестирование критических валют...")
        return self.test_currency_batch(critical_currencies)
    
    def get_all_eur_rates(self) -> Optional[Dict]:
        """Получает ВСЕ курсы к EUR за одну дату"""
        logger.info("📊 Получение всех курсов к EUR...")
        
        # Пробуем получить все доступные курсы
        url = f"{FRANKFURTER_BASE_URL}/{TEST_DATE}"
        
        for attempt in range(3):
            try:
                time.sleep(2 ** attempt)  # Экспоненциальная задержка
                
                response = self.session.get(url, timeout=60)  # Длинный таймаут
                if response.status_code == 200:
                    data = response.json()
                    eur_rates = data.get('rates', {})
                    eur_rates['EUR'] = 1.0
                    
                    logger.info(f"Получено {len(eur_rates)} курсов к EUR")
                    return eur_rates
                    
            except Exception as e:
                logger.warning(f"Попытка {attempt+1} не удалась: {e}")
        
        return None
    
    def calculate_pairs_from_eur_rates(self, eur_rates: Dict) -> Dict:
        """Рассчитывает пары на основе курсов к EUR"""
        if not eur_rates:
            return {"calculable": [], "non_calculable": PAIRS}
        
        calculable = []
        non_calculable = []
        
        for pair in PAIRS:
            base = pair[:3]
            quote = pair[3:]
            
            if base in eur_rates and quote in eur_rates:
                try:
                    # Избегаем деления на ноль
                    if eur_rates[base] == 0:
                        non_calculable.append(pair)
                        continue
                        
                    rate = eur_rates[quote] / eur_rates[base]
                    calculable.append(pair)
                    
                    if len(calculable) <= 10:  # Логируем только первые 10
                        logger.debug(f"✅ {pair}: {rate:.6f}")
                        
                except Exception as e:
                    non_calculable.append(pair)
            else:
                non_calculable.append(pair)
        
        return {
            "calculable": calculable,
            "non_calculable": non_calculable,
            "total": len(PAIRS),
            "coverage": len(calculable) / len(PAIRS) * 100
        }
    
    def run_quick_test(self) -> Dict:
        """Быстрый тест для оценки возможностей"""
        logger.info("🚀 Запуск быстрого теста Frankfurter.app")
        logger.info("=" * 50)
        
        try:
            # 1. Тест критических валют
            currency_test = self.test_critical_currencies()
            self.results["currency_coverage"] = currency_test
            
            logger.info(f"📊 Критические валюты: {len(currency_test['available'])}/"
                      f"{currency_test['total']} доступно "
                      f"({currency_test['coverage']:.1f}%)")
            
            # 2. Получение всех курсов к EUR
            eur_rates = self.get_all_eur_rates()
            
            if eur_rates:
                # 3. Расчет пар
                pair_test = self.calculate_pairs_from_eur_rates(eur_rates)
                self.results["pair_coverage"] = pair_test
                
                logger.info(f"📊 Пары: {len(pair_test['calculable'])}/"
                          f"{pair_test['total']} рассчитываемо "
                          f"({pair_test['coverage']:.1f}%)")
                
                # 4. Детальная информация
                self.results["eur_rates_sample"] = {
                    currency: rate for i, (currency, rate) in 
                    enumerate(eur_rates.items()) if i < 10
                }
                
                # 5. Анализ покрытия проекта
                self.analyze_project_coverage(currency_test['available'], pair_test['calculable'])
            
            # 6. Сохранение результатов
            self.save_results()
            
            return self.results
            
        except Exception as e:
            logger.error(f"❌ Ошибка теста: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def analyze_project_coverage(self, available_currencies: List[str], 
                                calculable_pairs: List[str]) -> None:
        """Анализирует покрытие проекта"""
        logger.info("\n📈 АНАЛИЗ ПОКРЫТИЯ ПРОЕКТА:")
        
        # Какие валюты проекта НЕ доступны
        unavailable = [c for c in CURRENCIES if c not in available_currencies]
        if unavailable:
            logger.warning(f"❌ Отсутствуют валюты проекта ({len(unavailable)}):")
            for curr in unavailable[:10]:  # Показываем первые 10
                logger.warning(f"   - {curr}: {CURRENCY_NAMES.get(curr, '')}")
            if len(unavailable) > 10:
                logger.warning(f"   ... и еще {len(unavailable) - 10}")
        
        # Какие пары проекта НЕ рассчитываются
        unavailable_pairs = [p for p in PAIRS if p not in calculable_pairs]
        if unavailable_pairs:
            logger.warning(f"❌ Не рассчитываются пары ({len(unavailable_pairs)}):")
            
            # Группируем по причинам
            eur_rates = self.get_all_eur_rates() or {}
            missing_currencies = {}
            
            for pair in unavailable_pairs[:15]:  # Показываем первые 15
                base = pair[:3]
                quote = pair[3:]
                missing = []
                if base not in eur_rates:
                    missing.append(base)
                if quote not in eur_rates:
                    missing.append(quote)
                
                if missing:
                    for curr in missing:
                        missing_currencies[curr] = missing_currencies.get(curr, 0) + 1
                
                logger.warning(f"   - {pair} (отсутствует: {', '.join(missing)})")
            
            if len(unavailable_pairs) > 15:
                logger.warning(f"   ... и еще {len(unavailable_pairs) - 15}")
            
            # Проблемные валюты
            if missing_currencies:
                logger.warning(f"\n🔍 ПРОБЛЕМНЫЕ ВАЛЮТЫ:")
                for curr, count in sorted(missing_currencies.items(), 
                                         key=lambda x: x[1], reverse=True)[:10]:
                    logger.warning(f"   - {curr}: влияет на {count} пар")
    
    def save_results(self):
        """Сохраняет результаты"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Краткий отчет
        report = {
            "timestamp": timestamp,
            "currency_coverage": self.results.get("currency_coverage", {}),
            "pair_coverage": self.results.get("pair_coverage", {}),
            "errors": self.results.get("errors", []),
            "recommendation": self.generate_recommendation()
        }
        
        # Сохраняем JSON
        json_file = RESULTS_DIR / f"quick_report_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Сохраняем текстовый отчет
        txt_file = RESULTS_DIR / f"summary_{timestamp}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_text_report())
        
        logger.info(f"\n💾 Результаты сохранены:")
        logger.info(f"   JSON: {json_file}")
        logger.info(f"   TXT:  {txt_file}")
    
    def generate_recommendation(self) -> str:
        """Генерирует рекомендацию"""
        currency_cov = self.results.get("currency_coverage", {}).get("coverage", 0)
        pair_cov = self.results.get("pair_coverage", {}).get("coverage", 0)
        
        if currency_cov >= 80 and pair_cov >= 80:
            return "ОТЛИЧНО - можно использовать как основной источник"
        elif currency_cov >= 60:
            return "ХОРОШО - основной источник для EUR-пар, дополнять другими API"
        elif currency_cov >= 40:
            return "УДОВЛЕТВОРИТЕЛЬНО - только для EUR-пар и основных валют"
        else:
            return "НИЗКОЕ ПОКРЫТИЕ - использовать ограниченно или искать альтернативы"
    
    def generate_text_report(self) -> str:
        """Генерирует текстовый отчет"""
        currency = self.results.get("currency_coverage", {})
        pairs = self.results.get("pair_coverage", {})
        
        report = [
            "=" * 60,
            "ОТЧЕТ ПО ТЕСТИРОВАНИЮ FRANKFURTER.APP ДЛЯ ABSCUR3",
            "=" * 60,
            f"Дата теста: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Проект: AbsCur3 (45 валют, 85 пар)",
            "",
            "📊 РЕЗУЛЬТАТЫ:",
            f"  Валюты: {currency.get('coverage', 0):.1f}% "
            f"({len(currency.get('available', []))}/{currency.get('total', 0)})",
            f"  Пары:   {pairs.get('coverage', 0):.1f}% "
            f"({len(pairs.get('calculable', []))}/{pairs.get('total', 0)})",
            "",
            "🎯 РЕКОМЕНДАЦИЯ:",
            f"  {self.generate_recommendation()}",
            "",
            "=" * 60
        ]
        
        return "\n".join(report)


def main():
    """Основная функция"""
    print("\n" + "=" * 60)
    print("🔍 ABScur3 - Быстрое тестирование Frankfurter.app")
    print("=" * 60)
    print("Тестирование займет 1-2 минуты...\n")
    
    tester = RobustFrankfurterTester()
    results = tester.run_quick_test()
    
    if results:
        print("\n✅ Тестирование завершено!")
        print(f"📁 Результаты в: {RESULTS_DIR}")
    else:
        print("\n❌ Тестирование не удалось")
        print("Попробуйте:")
        print("1. Проверить интернет-соединение")
        print("2. Запустить позже (возможно, временные проблемы с API)")
        print("3. Использовать VPN")


if __name__ == "__main__":
    main()
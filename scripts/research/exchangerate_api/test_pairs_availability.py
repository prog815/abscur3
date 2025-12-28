"""
Исследование доступности валютных пар через ExchangeRate-API.
Проверяет, какие пары можно получить напрямую, а какие нужно рассчитывать.
"""
import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dotenv import load_dotenv
from datetime import datetime

# ================== НАСТРОЙКА ==================
# Предполагаем запуск из корня проекта
current_dir = Path.cwd()
env_path = current_dir / '.env'

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"✅ Загружены переменные из .env")
else:
    print(f"❌ Файл .env не найден!")
    sys.exit(1)

# Загружаем список пар из проекта
sys.path.insert(0, str(current_dir / 'scripts' / 'research'))
try:
    from currencies import PAIRS  # Предполагаем, что PAIRS есть в currencies.py
    print(f"✅ Загружено {len(PAIRS)} пар из модуля 'currencies'")
except ImportError:
    print("❌ Не удалось загрузить список пар. Завершаю выполнение.")
    sys.exit(1)

# Конфигурация API
ENV_VAR_NAME = 'EXCHANGERATE_API_KEY'
API_KEY = os.getenv(ENV_VAR_NAME)
if not API_KEY:
    print(f"❌ Не найден ключ API в переменной '{ENV_VAR_NAME}'")
    sys.exit(1)

API_BASE_URL = 'https://v6.exchangerate-api.com/v6'
BASE_CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 'NZD']  # Основные базовые валюты
# ===============================================

def test_pair_direct(base: str, target: str) -> bool:
    """Проверяет, доступна ли пара напрямую (например, USD/EUR)."""
    url = f"{API_BASE_URL}/{API_KEY}/pair/{base}/{target}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        return data.get('result') == 'success'
    except:
        return False

def test_base_currency_availability(base: str) -> Dict[str, float]:
    """Проверяет, какие валюты доступны относительно базовой."""
    url = f"{API_BASE_URL}/{API_KEY}/latest/{base}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get('result') == 'success':
            return data.get('conversion_rates', {})
    except:
        pass
    return {}

def analyze_pairs_coverage():
    """Основная функция анализа доступности пар."""
    print("\n" + "="*70)
    print("АНАЛИЗ ДОСТУПНОСТИ ВАЛЮТНЫХ ПАР В EXCHANGERATE-API")
    print("="*70)
    
    # Шаг 1: Проверяем доступность базовых валют
    print("\n🔍 Проверяем доступные базовые валюты...")
    available_bases = []
    base_coverage = {}
    
    for base in BASE_CURRENCIES:
        print(f"   Проверяем {base}...", end=" ")
        rates = test_base_currency_availability(base)
        if rates:
            available_bases.append(base)
            base_coverage[base] = rates
            print(f"✅ Доступно {len(rates)} валют")
            # Пауза для соблюдения лимитов API
            time.sleep(0.5)
        else:
            print(f"❌ Недоступно")
    
    print(f"\n📊 Доступные базовые валюты: {', '.join(available_bases)}")
    
    # Шаг 2: Анализируем покрытие пар проекта
    print("\n📈 Анализируем покрытие пар проекта...")
    
    directly_available = []
    calculated = []
    unavailable = []
    
    for i, pair in enumerate(PAIRS, 1):
        if len(pair) != 6:  # Например, 'USDRUB' -> 6 символов
            print(f"⚠️  Пропускаю некорректную пару: {pair}")
            continue
            
        base = pair[:3]
        target = pair[3:]
        
        print(f"  {i:3d}/{len(PAIRS)}: {pair} ({base}/{target})...", end=" ")
        
        # Проверяем возможность прямого запроса
        if test_pair_direct(base, target):
            directly_available.append(pair)
            print("✅ Напрямую")
        else:
            # Проверяем, можно ли рассчитать через доступные базы
            can_calculate = False
            for available_base in available_bases:
                if (base in base_coverage.get(available_base, {}) and 
                    target in base_coverage.get(available_base, {})):
                    can_calculate = True
                    break
            
            if can_calculate:
                calculated.append(pair)
                print("🔀 Через расчёт")
            else:
                unavailable.append(pair)
                print("❌ Недоступно")
        
        # Пауза для соблюдения лимитов API (важно для бесплатного тарифа!)
        if i % 10 == 0:
            time.sleep(1)
    
    # Шаг 3: Формируем отчёт
    print("\n" + "="*70)
    print("РЕЗУЛЬТАТЫ АНАЛИЗА")
    print("="*70)
    
    total_pairs = len(PAIRS)
    print(f"Всего пар в проекте: {total_pairs}")
    print(f"✅ Доступно напрямую: {len(directly_available)} ({len(directly_available)/total_pairs*100:.1f}%)")
    print(f"🔀 Доступно через расчёт: {len(calculated)} ({len(calculated)/total_pairs*100:.1f}%)")
    print(f"❌ Недоступно: {len(unavailable)} ({len(unavailable)/total_pairs*100:.1f}%)")
    
    if unavailable:
        print(f"\n⚠️  Проблемные пары ({len(unavailable)}):")
        # Группируем по типу проблемы
        unusual_bases = set()
        unusual_targets = set()
        
        for pair in unavailable:
            base = pair[:3]
            target = pair[3:]
            unusual_bases.add(base)
            unusual_targets.add(target)
        
        print(f"   Необычные базовые валюты: {', '.join(sorted(unusual_bases))}")
        print(f"   Необычные целевые валюты: {', '.join(sorted(unusual_targets))}")
    
    # Шаг 4: Сохраняем детальный отчёт
    save_detailed_report(
        available_bases=available_bases,
        directly_available=directly_available,
        calculated=calculated,
        unavailable=unavailable,
        base_coverage=base_coverage
    )
    
    return directly_available, calculated, unavailable

def save_detailed_report(available_bases, directly_available, calculated, unavailable, base_coverage):
    """Сохраняет детальный отчёт в JSON."""
    report = {
        'timestamp': datetime.now().isoformat(),
        'api_used': 'ExchangeRate-API',
        'plan': 'Free',
        'available_base_currencies': available_bases,
        'pairs_analysis': {
            'total': len(directly_available) + len(calculated) + len(unavailable),
            'directly_available': {
                'count': len(directly_available),
                'pairs': directly_available
            },
            'calculated': {
                'count': len(calculated),
                'pairs': calculated
            },
            'unavailable': {
                'count': len(unavailable),
                'pairs': unavailable
            }
        },
        'coverage_by_base': {}
    }
    
    # Добавляем информацию о покрытии по каждой базовой валюте
    for base, rates in base_coverage.items():
        report['coverage_by_base'][base] = {
            'total_rates': len(rates),
            'sample_rates': dict(list(rates.items())[:5])  # Первые 5 курсов для примера
        }
    
    # Сохраняем в файл
    output_dir = current_dir / 'data' / 'research_results' / 'exchangerate_api'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename = output_dir / f'pairs_coverage_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Детальный отчёт сохранён: {filename}")
    
    # Также сохраняем краткую сводку в текстовый файл
    txt_filename = output_dir / 'pairs_coverage_summary.txt'
    with open(txt_filename, 'w', encoding='utf-8') as f:
        f.write("АНАЛИЗ ДОСТУПНОСТИ ВАЛЮТНЫХ ПАР\n")
        f.write("="*50 + "\n\n")
        f.write(f"Дата анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"API: ExchangeRate-API (Free plan)\n")
        f.write(f"Доступные базовые валюты: {', '.join(available_bases)}\n\n")
        
        f.write(f"ВСЕГО ПАР: {report['pairs_analysis']['total']}\n")
        f.write(f"✅ Напрямую доступно: {len(directly_available)} пар\n")
        f.write(f"🔀 Доступно через расчёт: {len(calculated)} пар\n")
        f.write(f"❌ Недоступно: {len(unavailable)} пар\n\n")
        
        if unavailable:
            f.write("НЕДОСТУПНЫЕ ПАРЫ:\n")
            for pair in sorted(unavailable):
                f.write(f"  {pair[:3]}/{pair[3:]}\n")
    
    print(f"📝 Краткая сводка сохранена: {txt_filename}")

def main():
    """Основная функция."""
    print("🚀 Запуск анализа доступности валютных пар")
    print(f"💡 Используется бесплатный тариф - добавляем паузы между запросами")
    
    # Для бесплатного тарифа добавляем дополнительные паузы
    print("⏸️  Пауза 2 секунды перед началом...")
    time.sleep(2)
    
    try:
        directly_available, calculated, unavailable = analyze_pairs_coverage()
        
        # Рекомендации по результатам
        print("\n" + "="*70)
        print("💡 РЕКОМЕНДАЦИИ ДЛЯ ПРОЕКТА ABSCUR3")
        print("="*70)
        
        if len(directly_available) / len(PAIRS) > 0.8:
            print("✅ Отличное покрытие! Большинство пар доступны напрямую.")
        elif len(unavailable) == 0:
            print("✅ Хорошее покрытие! Все пары доступны (напрямую или через расчёт).")
        else:
            print(f"⚠️  Есть {len(unavailable)} недоступных пар. Возможные решения:")
            print("   1. Проверить корректность кодов валют")
            print("   2. Использовать альтернативный API для проблемных пар")
            print("   3. Перейти на платный тариф для расширенных возможностей")
        
        print(f"\n📊 Для ETL-пайплайна можно использовать:")
        print(f"   • Прямые запросы для {len(directly_available)} пар")
        print(f"   • Расчёт через базовые валюты для {len(calculated)} пар")
        
    except Exception as e:
        print(f"\n❌ Ошибка при анализе: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
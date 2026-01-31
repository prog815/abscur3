"""
Скрипт инкрементального ежедневного обновления данных для проекта AbsCur3.
Логика: last_local_date - 5 дней → yesterday
Батчи по 7 пар с ожиданием до следующей минуты.
Запуск из корня проекта: python scripts/daily_update/incremental_updater.py
"""

import requests
import time
import json
import os
import csv
import logging
import random
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# --- Конфигурация (наследуем из historical_loader с изменениями) ---

# Загружаем переменные из .env
load_dotenv()

API_KEY = os.getenv('TWELVE_DATA_API_KEY')
BASE_URL = 'https://api.twelvedata.com'
INTERVAL = '1day'  # Дневные данные

# Предполагаем, что скрипт запускается из корня проекта
PROJECT_ROOT = os.getcwd()

# Лимиты API Twelve Data (Basic Plan)
REQUESTS_PER_MINUTE_LIMIT = 8
# Рабочий лимит: 7 запросов в минуту, 1 в резерве
SAFE_REQUESTS_PER_MINUTE = 7

# Количество дней перекрытия (из ТЗ)
OVERLAP_DAYS = 5

# Пути для данных
DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'raw', 'twelve_data', 'pairs')
METADATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'metadata')
DAILY_UPDATE_DIR = os.path.join(PROJECT_ROOT, 'scripts', 'daily_update')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)
os.makedirs(DAILY_UPDATE_DIR, exist_ok=True)

# Файлы состояния и логов
UPDATE_STATE_FILE = os.path.join(METADATA_DIR, 'update_state.json')
LOG_DIR = os.path.join(DAILY_UPDATE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f'update_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

# Настройка логирования (ИСПРАВЛЕННАЯ ВЕРСИЯ)
def setup_logging():
    """Настройка логирования с учётом особенностей Windows."""
    import sys
    
    # Создаем форматтер
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Обработчик для файла
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Обработчик для консоли с обработкой ошибок кодировки
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Для Windows: заменяем проблемные символы
    if sys.platform.startswith('win'):
        # Создаем фильтр для замены неподдерживаемых символов
        class SafeEncodingFilter(logging.Filter):
            def filter(self, record):
                if hasattr(record, 'msg'):
                    # Заменяем символы, которые могут вызывать проблемы в Windows
                    replacements = {
                        '→': '->',
                        '—': '-',
                        '–': '-',
                        '…': '...',
                    }
                    for old, new in replacements.items():
                        if old in record.msg:
                            record.msg = record.msg.replace(old, new)
                return True
        
        console_handler.addFilter(SafeEncodingFilter())
    
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

# Вместо старой настройки логирования:
# logging.basicConfig(...)
# logger = logging.getLogger(__name__)

# Используем новую настройку
logger = setup_logging()

def load_currency_config():
    """
    Загружает список валютных пар из конфигурационного файла.
    Возвращает список символов.
    Для тестирования: возвращает случайные 10 пар из всех доступных.
    """
    config_file = os.path.join(PROJECT_ROOT, 'config', 'currencies.py')
    
    if not os.path.exists(config_file):
        logger.error(f"Конфигурационный файл не найден: {config_file}")
        logger.warning("Использую тестовый список из 5 пар")
        return ["USD/RUB", "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]
    
    try:
        # Динамически импортируем конфигурацию
        import importlib.util
        spec = importlib.util.spec_from_file_location("currencies", config_file)
        currencies_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(currencies_module)
        
        if hasattr(currencies_module, 'ALL_SYMBOLS'):
            all_symbols = currencies_module.ALL_SYMBOLS
            logger.info(f"Загружено {len(all_symbols)} пар из конфигурационного файла")
            
            # ТЕСТОВЫЙ РЕЖИМ: выбираем случайные 10 пар
            if all_symbols:
                import random
                # Фиксируем seed для воспроизводимости тестов
                random.seed(42)  # Можно убрать для полностью случайного выбора
                
                # Проверяем, что пар достаточно для выборки
                sample_size = min(10, len(all_symbols))
                selected_pairs = random.sample(all_symbols, sample_size)
                
                logger.info(f"ТЕСТОВЫЙ РЕЖИМ: выбрано {len(selected_pairs)} случайных пар:")
                for i, pair in enumerate(selected_pairs, 1):
                    logger.info(f"  {i}. {pair}")
                
                return selected_pairs
            else:
                logger.error("Список пар пуст в конфигурационном файле")
                return []
        else:
            logger.error("В конфигурационном файле не найден ALL_SYMBOLS")
            return []
            
    except Exception as e:
        logger.error(f"Ошибка загрузки конфигурации: {e}")
        return []


# --- Наследуемые утилиты из historical_loader.py ---

def make_request(endpoint, params, max_retries=3):
    """
    Универсальная функция для выполнения запроса с контролем лимитов.
    Возвращает JSON-ответ или None в случае ошибки.
    """
    url = f'{BASE_URL}{endpoint}'
    all_params = {'apikey': API_KEY, **params}

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=all_params, timeout=30)
            
            # Проверяем заголовки с оставшимися кредитами
            credits_left = response.headers.get('api-credits-left')
            if credits_left:
                logger.debug(f"Осталось кредитов API: {credits_left}")

            if response.status_code == 429:
                logger.warning(f"Достигнут лимит запросов (429). Пауза 60 сек.")
                time.sleep(60)
                continue

            if response.status_code != 200:
                logger.error(f"Ошибка HTTP {response.status_code}: {response.text}")
                return None

            data = response.json()
            if data.get('status') == 'error':
                logger.error(f"Ошибка API: {data.get('message')}")
                return None

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Сетевая ошибка (попытка {attempt+1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
    return None

def get_existing_data_info(symbol):
    """
    Проверяет существующие данные для пары и возвращает информацию о них.
    Возвращает кортеж: (exists, last_date, total_rows)
    """
    filename = os.path.join(DATA_DIR, f'{symbol.replace("/", "")}.csv')
    
    if not os.path.exists(filename):
        logger.debug(f"Файл для {symbol} не существует")
        return False, None, 0
    
    try:
        last_date = None
        total_rows = 0
        
        with open(filename, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            total_rows = len(rows)
            
            if rows:
                last_date = rows[-1]['datetime']
                logger.debug(f"Для {symbol} найдено {total_rows} записей, последняя дата: {last_date}")
            else:
                logger.warning(f"Файл для {symbol} существует, но пуст")
                return True, None, 0
        
        return True, last_date, total_rows
        
    except Exception as e:
        logger.error(f"Ошибка чтения файла для {symbol}: {e}")
        return True, None, 0

def fetch_historical_chunk(symbol, start_date, end_date):
    """
    Загружает исторические данные за указанный период.
    Параметры start_date и end_date должны быть строкой в формате 'YYYY-MM-DD'.
    """
    logger.debug(f"Загрузка {symbol} с {start_date} по {end_date}")
    params = {
        'symbol': symbol,
        'interval': INTERVAL,
        'start_date': start_date,
        'end_date': end_date,
        'order': 'asc'  # От старых к новым
    }
    return make_request('/time_series', params)

def save_to_csv(symbol, data_points):
    """
    Сохраняет загруженные данные в CSV файл, сортируя по дате и удаляя дубликаты.
    Приоритет у данных из нового запроса (для перезаписи).
    """
    if not data_points:
        logger.warning(f"Нет данных для сохранения {symbol}")
        return 0
    
    filename = os.path.join(DATA_DIR, f'{symbol.replace("/", "")}.csv')
    
    # 1. Создаём словарь из новых данных
    new_data_dict = {}
    for point in data_points:
        date = point['datetime']
        # Проверяем корректность формата даты
        try:
            datetime.strptime(date, '%Y-%m-%d')
            new_data_dict[date] = {
                'datetime': date,
                'open': point.get('open', ''),
                'high': point.get('high', ''),
                'low': point.get('low', ''),
                'close': point.get('close', '')
            }
        except ValueError:
            logger.warning(f"Пропускаю некорректную дату '{date}' для {symbol}")
    
    # 2. Загружаем существующие данные (если файл есть)
    existing_data_dict = {}
    if os.path.exists(filename):
        try:
            with open(filename, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_data_dict[row['datetime']] = row
            logger.debug(f"Загружено {len(existing_data_dict)} существующих записей для {symbol}")
        except Exception as e:
            logger.error(f"Ошибка чтения файла {filename}: {e}")
            # Создаём backup повреждённого файла
            backup_name = f"{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M')}"
            os.rename(filename, backup_name)
            logger.info(f"Создан backup повреждённого файла: {backup_name}")
    
    # 3. Объединяем данные (новые перезаписывают старые при конфликте)
    merged_data = {**existing_data_dict, **new_data_dict}
    
    # 4. Сортируем по дате (от старых к новым)
    sorted_dates = sorted(merged_data.keys())
    sorted_rows = [merged_data[date] for date in sorted_dates]
    
    # 5. Сохраняем отсортированные данные
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['datetime', 'open', 'high', 'low', 'close']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sorted_rows)
        
        added_count = len(new_data_dict)
        updated_count = len([d for d in new_data_dict.keys() if d in existing_data_dict])
        total_count = len(sorted_rows)
        
        logger.info(f"Сохранено {total_count} записей для {symbol}: "
                   f"добавлено {added_count - updated_count} новых, "
                   f"обновлено {updated_count} существующих")
        
        return added_count - updated_count  # Возвращаем количество новых записей
        
    except Exception as e:
        logger.error(f"Ошибка записи файла {filename}: {e}")
        return 0

class RateLimiter:
    """Простейший счетчик для соблюдения лимита запросов в минуту."""
    def __init__(self, max_per_minute):
        self.max_per_minute = max_per_minute
        self.request_timestamps = []
        self.total_requests = 0  # Счетчик всех запросов

    def wait_if_needed(self):
        """Делает паузу, если лимит за минуту исчерпан."""
        now = time.time()
        minute_ago = now - 60
        # Оставляем только запросы за последнюю минуту
        self.request_timestamps = [ts for ts in self.request_timestamps if ts > minute_ago]

        if len(self.request_timestamps) >= self.max_per_minute:
            sleep_time = 60 - (now - self.request_timestamps[0]) + 1  # +1 сек на всякий случай
            logger.info(f"Достигнут лимит {self.max_per_minute} запр/мин. Пауза {sleep_time:.1f} сек.")
            time.sleep(sleep_time)
            # Обновляем время после сна
            now = time.time()

        self.request_timestamps.append(now)
        self.total_requests += 1

    def get_total_requests(self):
        """Возвращает общее количество выполненных запросов."""
        return self.total_requests

# --- Новая логика инкрементального обновления ---

def get_yesterday_date():
    """Возвращает дату вчерашнего дня в формате YYYY-MM-DD."""
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime('%Y-%m-%d')

def calculate_update_range(last_local_date_str):
    """
    Рассчитывает диапазон обновления: last_local_date - 5 дней → yesterday.
    Возвращает (start_date, end_date) или (None, None) если обновление не нужно.
    """
    try:
        last_local_date = datetime.strptime(last_local_date_str, '%Y-%m-%d')
    except ValueError:
        logger.error(f"Некорректный формат даты: {last_local_date_str}")
        return None, None
    
    # Вычитаем 5 дней для перекрытия
    start_date = last_local_date - timedelta(days=OVERLAP_DAYS)
    end_date = datetime.now() - timedelta(days=1)  # Вчерашний день
    
    # Если start_date >= end_date, обновление не нужно
    if start_date >= end_date:
        return None, None
    
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

def update_single_pair(symbol, rate_limiter):
    """
    Обновляет данные для одной валютной пары.
    Возвращает dict с результатами.
    """
    logger.info(f"--- Начинаю обновление для {symbol} ---")
    
    # 1. Проверяем существующие данные
    exists, last_date, existing_rows = get_existing_data_info(symbol)
    
    if not exists:
        logger.warning(f"Для {symbol} нет локальных данных. Пропускаем (нужна первоначальная загрузка).")
        return {
            'symbol': symbol,
            'status': 'no_local_data',
            'existing_rows': 0,
            'new_rows': 0,
            'error': 'Нет локальных данных для инкрементального обновления'
        }
    
    if not last_date:
        logger.warning(f"Для {symbol} не удалось определить последнюю дату. Пропускаем.")
        return {
            'symbol': symbol,
            'status': 'no_last_date',
            'existing_rows': existing_rows,
            'new_rows': 0,
            'error': 'Не удалось определить последнюю дату'
        }
    
    # 2. Рассчитываем диапазон обновления
    start_date, end_date = calculate_update_range(last_date)
    
    if not start_date or not end_date:
        logger.info(f"Для {symbol} обновление не требуется (данные актуальны до {last_date})")
        return {
            'symbol': symbol,
            'status': 'already_current',
            'existing_rows': existing_rows,
            'new_rows': 0,
            'last_date': last_date
        }
    
    logger.info(f"Диапазон обновления для {symbol}: {start_date} → {end_date}")
    
    # 3. Загружаем данные
    rate_limiter.wait_if_needed()
    data = fetch_historical_chunk(symbol, start_date, end_date)
    
    if not data or 'values' not in data:
        logger.error(f"Не удалось загрузить данные для {symbol}")
        return {
            'symbol': symbol,
            'status': 'failed',
            'existing_rows': existing_rows,
            'new_rows': 0,
            'error': 'Ошибка загрузки данных',
            'range': f"{start_date} - {end_date}"
        }
    
    # 4. Сохраняем данные
    values = data['values']
    values.reverse()  # API возвращает от новых к старым
    
    if values:
        new_rows = save_to_csv(symbol, values)
        latest_date = values[-1]['datetime'] if values else last_date
        
        logger.info(f"Обновление {symbol} завершено: добавлено {new_rows} новых записей")
        return {
            'symbol': symbol,
            'status': 'updated',
            'existing_rows': existing_rows,
            'new_rows': new_rows,
            'last_date': latest_date,
            'range': f"{start_date} - {end_date}"
        }
    else:
        logger.warning(f"Нет новых данных для {symbol} в диапазоне {start_date} - {end_date}")
        return {
            'symbol': symbol,
            'status': 'no_new_data',
            'existing_rows': existing_rows,
            'new_rows': 0,
            'last_date': last_date,
            'range': f"{start_date} - {end_date}"
        }

def wait_until_next_minute():
    """Ожидает до начала следующей календарной минуты."""
    now = datetime.now()
    seconds_to_next_minute = 60 - now.second
    logger.info(f"Ожидание {seconds_to_next_minute} сек. до следующей минуты...")
    time.sleep(seconds_to_next_minute + 0.1)  # +0.1 для надёжности

def save_update_state(results, stats, total_requests):
    """Сохраняет состояние обновления в JSON файл."""
    state = {
        'timestamp': datetime.now().isoformat(),
        'total_pairs': len(results),
        'total_api_requests': total_requests,
        'yesterday_date': get_yesterday_date(),
        'statistics': stats,
        'results': results
    }
    
    try:
        with open(UPDATE_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        logger.info(f"Состояние обновления сохранено в {UPDATE_STATE_FILE}")
    except Exception as e:
        logger.error(f"Ошибка сохранения состояния: {e}")

def main():
    """
    Главная функция инкрементального обновления.
    """
    logger.info("=" * 60)
    logger.info(f"ЗАПУСК ИНКРЕМЕНТАЛЬНОГО ОБНОВЛЕНИЯ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Корень проекта: {PROJECT_ROOT}")
    logger.info(f"Логи будут сохранены в: {LOG_FILE}")
    logger.info(f"Файл состояния: {UPDATE_STATE_FILE}")
    
    # Проверка API ключа
    if not API_KEY:
        logger.error("API ключ не найден. Убедитесь, что переменная TWELVE_DATA_API_KEY установлена в .env файле.")
        return 1
    
    # Загружаем список пар
    currency_pairs = load_currency_config()
    
    if not currency_pairs:
        logger.error("Не удалось загрузить список валютных пар. Завершение.")
        return 1
    
    logger.info(f"Загружено {len(currency_pairs)} валютных пар")
    
    # Случайное перемешивание пар
    random.shuffle(currency_pairs)
    logger.info("Список пар случайно перемешан")
    
    # Инициализируем RateLimiter
    rate_limiter = RateLimiter(SAFE_REQUESTS_PER_MINUTE)
    
    # Статистика
    stats = {
        'updated': 0,
        'already_current': 0,
        'no_new_data': 0,
        'failed': 0,
        'no_local_data': 0,
        'no_last_date': 0,
        'total_new_rows': 0,
        'total_existing_rows': 0
    }
    
    results = {}
    pairs_to_update = []
    
    # Фильтруем пары, требующие обновления (быстрая проверка)
    logger.info("Предварительная проверка пар...")
    for symbol in currency_pairs:
        exists, last_date, existing_rows = get_existing_data_info(symbol)
        if exists and last_date:
            start_date, end_date = calculate_update_range(last_date)
            if start_date and end_date:
                pairs_to_update.append(symbol)
        else:
            logger.debug(f"Пара {symbol} пропущена на этапе предпроверки")
    
    logger.info(f"Из {len(currency_pairs)} пар требуется обновление для {len(pairs_to_update)}")
    
    if not pairs_to_update:
        logger.info("Нет пар, требующих обновления. Завершение.")
        save_update_state({}, stats, 0)
        return 0
    
    # Обработка пар батчами по 7
    BATCH_SIZE = 7
    total_batches = (len(pairs_to_update) + BATCH_SIZE - 1) // BATCH_SIZE
    
    logger.info(f"Начинаю обработку {len(pairs_to_update)} пар в {total_batches} батчах по {BATCH_SIZE}")
    logger.info(f"Ожидаемое время: ~{total_batches} минут")
    
    for batch_num in range(total_batches):
        logger.info(f"--- Батч {batch_num + 1}/{total_batches} ---")
        
        start_idx = batch_num * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, len(pairs_to_update))
        batch_pairs = pairs_to_update[start_idx:end_idx]
        
        batch_start_time = time.time()
        
        # Обрабатываем пары в батче
        for symbol in batch_pairs:
            try:
                result = update_single_pair(symbol, rate_limiter)
                results[symbol] = result
                
                # Обновляем статистику
                stats[result['status']] += 1
                stats['total_new_rows'] += result.get('new_rows', 0)
                stats['total_existing_rows'] += result.get('existing_rows', 0)
                
            except Exception as e:
                logger.error(f"Критическая ошибка при обработке {symbol}: {e}")
                results[symbol] = {
                    'symbol': symbol,
                    'status': 'exception',
                    'error': str(e)
                }
                stats['failed'] += 1
        
        batch_time = time.time() - batch_start_time
        logger.info(f"Батч {batch_num + 1} обработан за {batch_time:.1f} сек.")
        
        # Если это не последний батч, ждём следующей минуты
        if batch_num < total_batches - 1:
            wait_until_next_minute()
    
    # Итоговый отчет
    logger.info("=" * 60)
    logger.info("ИНКРЕМЕНТАЛЬНОЕ ОБНОВЛЕНИЕ ЗАВЕРШЕНО")
    logger.info(f"Всего обработано пар: {len(currency_pairs)}")
    logger.info(f"Требовали обновления: {len(pairs_to_update)}")
    logger.info(f"Всего запросов к API: {rate_limiter.get_total_requests()}")
    logger.info("")
    logger.info("=== СТАТИСТИКА ===")
    logger.info(f"Успешно обновлены: {stats['updated']} пар")
    logger.info(f"Уже актуальны: {stats['already_current']} пар")
    logger.info(f"Нет новых данных: {stats['no_new_data']} пар")
    logger.info(f"Ошибки загрузки: {stats['failed']} пар")
    logger.info(f"Нет локальных данных: {stats['no_local_data']} пар")
    logger.info(f"Нет последней даты: {stats['no_last_date']} пар")
    logger.info("")
    logger.info(f"Всего существующих записей: {stats['total_existing_rows']}")
    logger.info(f"Всего новых записей: {stats['total_new_rows']}")
    logger.info("")
    logger.info(f"Лог сохранен: {LOG_FILE}")
    
    # Сохраняем состояние
    save_update_state(results, stats, rate_limiter.get_total_requests())
    
    return 0

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Обновление прервано пользователем")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        sys.exit(1)
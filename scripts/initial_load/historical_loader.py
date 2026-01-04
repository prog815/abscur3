import requests
import time
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import csv
import logging


# --- Конфигурация ---
load_dotenv()  # Загружает переменные из .env
API_KEY = os.getenv('TWELVE_DATA_API_KEY')
BASE_URL = 'https://api.twelvedata.com'
INTERVAL = '1day'  # Дневные данные

# Предполагаем, что скрипт запускается из корня проекта
PROJECT_ROOT = os.getcwd()

# Лимиты сервиса (Basic Plan)
REQUESTS_PER_MINUTE_LIMIT = 8
# Рабочий лимит: оставляем 1 запрос в минуту "про запас"
SAFE_REQUESTS_PER_MINUTE = 7
MAX_POINTS_PER_REQUEST = 5000  # Макс. баров в одном ответе

# Пути для сохранения данных (относительно корня проекта)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'raw', 'twelve_data', 'pairs')
METADATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'raw', 'twelve_data', 'metadata')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)
EARLIEST_DATES_FILE = os.path.join(METADATA_DIR, 'earliest_dates.json')
LAST_UPDATE_FILE = os.path.join(METADATA_DIR, 'last_update.json')

# Путь для логов
LOG_DIR = os.path.join(PROJECT_ROOT, 'scripts', 'initial_load', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f'initial_load_{datetime.now().strftime("%Y%m%d_%H%M")}.log')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_currency_config():
    """
    Загружает список валютных пар из конфигурационного файла.
    Возвращает список символов.
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
            symbols = currencies_module.ALL_SYMBOLS
            logger.info(f"Загружено {len(symbols)} пар из конфигурационного файла")
            return symbols
        else:
            logger.error("В конфигурационном файле не найден ALL_SYMBOLS")
            return []
            
    except Exception as e:
        logger.error(f"Ошибка загрузки конфигурации: {e}")
        return []

# --- Утилиты для работы с API ---
def make_request(endpoint, params, request_type='history'):
    """
    Универсальная функция для выполнения запроса с контролем лимитов.
    Возвращает JSON-ответ или None в случае ошибки.
    """
    url = f'{BASE_URL}{endpoint}'
    all_params = {'apikey': API_KEY, **params}

    for attempt in range(3):  # 3 попытки
        try:
            response = requests.get(url, params=all_params, timeout=30)
            # Проверяем заголовки с оставшимися кредитами [citation:7]
            credits_left = response.headers.get('api-credits-left')
            if credits_left:
                logger.debug(f"Осталось кредитов API: {credits_left}")

            if response.status_code == 429:
                logger.warning(f"Достигнут лимит запросов (429). Пауза 60 сек.")
                time.sleep(60)
                continue

            if response.status_code != 200:
                logger.error(f"Ошибка HTTP {response.status_code} для {params.get('symbol', '')}: {response.text}")
                return None

            data = response.json()
            if data.get('status') == 'error':
                logger.error(f"Ошибка API для {params.get('symbol', '')}: {data.get('message')}")
                return None

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Сетевая ошибка (попытка {attempt+1}) для {params.get('symbol', '')}: {e}")
            time.sleep(5)
    return None

def get_earliest_timestamp(symbol):
    """
    Определяет самую раннюю доступную дату для пары.
    Использует эндпоинт /earliest_timestamp [citation:3].
    """
    # Сначала проверяем кэш
    if os.path.exists(EARLIEST_DATES_FILE):
        with open(EARLIEST_DATES_FILE, 'r') as f:
            cache = json.load(f)
            if symbol in cache:
                logger.info(f"Ранняя дата для {symbol} найдена в кэше: {cache[symbol]}")
                return cache[symbol]

    logger.info(f"Запрос самой ранней даты для {symbol}...")
    params = {'symbol': symbol, 'interval': INTERVAL}
    data = make_request('/earliest_timestamp', params, 'earliest')

    if data and 'datetime' in data:
        earliest_date = data['datetime'].split(' ')[0]  # Берем только дату
        # Сохраняем в кэш
        cache = {}
        if os.path.exists(EARLIEST_DATES_FILE):
            with open(EARLIEST_DATES_FILE, 'r') as f:
                cache = json.load(f)
        cache[symbol] = earliest_date
        with open(EARLIEST_DATES_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
        logger.info(f"Самая ранняя дата для {symbol}: {earliest_date}")
        return earliest_date
    else:
        logger.warning(f"Не удалось определить раннюю дату для {symbol}. Использую 2000-01-01.")
        return '2000-01-01'  # Консервативное значение по умолчанию

def get_latest_available_date(symbol):
    """
    Определяет последнюю доступную дату для пары через API.
    Это нужно для проверки, есть ли новые данные.
    """
    logger.debug(f"Запрос последней доступной даты для {symbol}...")
    # Используем эндпоинт time_series с минимальным периодом
    params = {
        'symbol': symbol,
        'interval': INTERVAL,
        'outputsize': 1,  # Только последняя запись
        'order': 'desc'
    }
    
    data = make_request('/time_series', params)
    
    if data and 'values' in data and data['values']:
        latest_date = data['values'][0]['datetime'].split(' ')[0]
        logger.debug(f"Последняя доступная дата для {symbol}: {latest_date}")
        return latest_date
    
    logger.warning(f"Не удалось определить последнюю доступную дату для {symbol}")
    return None

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
        # Читаем только последние несколько строк, чтобы найти последнюю дату
        last_date = None
        total_rows = 0
        
        with open(filename, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            total_rows = len(rows)
            
            if rows:
                # Данные уже отсортированы по возрастанию, последняя строка - самая новая
                last_date = rows[-1]['datetime']
                logger.debug(f"Для {symbol} найдено {total_rows} записей, последняя дата: {last_date}")
            else:
                logger.warning(f"Файл для {symbol} существует, но пуст")
                return True, None, 0
        
        return True, last_date, total_rows
        
    except Exception as e:
        logger.error(f"Ошибка чтения файла для {symbol}: {e}")
        return True, None, 0

# --- Основная логика загрузки ---
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

def save_to_csv(symbol, data_points):
    """Сохраняет загруженные данные в CSV файл, сортируя по дате и удаляя дубликаты."""
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
            logger.info(f"Загружено {len(existing_data_dict)} существующих записей для {symbol}")
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

def load_pair_history(symbol, rate_limiter, force_reload=False):
    """
    Основная функция загрузки истории для одной валютной пары.
    Если force_reload=False, загружает только недостающие данные.
    """
    logger.info(f"--- Начинаю загрузку для {symbol} ---")

    # 1. Проверяем существующие данные
    exists, last_date, existing_rows = get_existing_data_info(symbol)
    
    if exists and last_date and not force_reload:
        # Проверяем, нужна ли догрузка данных
        logger.info(f"Для {symbol} уже загружено {existing_rows} записей до {last_date}")
        
        # Проверяем, есть ли новые данные в API
        rate_limiter.wait_if_needed()
        latest_available_date = get_latest_available_date(symbol)
        
        if latest_available_date:
            # Преобразуем даты для сравнения
            last_dt = datetime.strptime(last_date, '%Y-%m-%d')
            latest_dt = datetime.strptime(latest_available_date, '%Y-%m-%d')
            
            if latest_dt <= last_dt:
                logger.info(f"Для {symbol} уже есть все актуальные данные (до {last_date})")
                return {
                    'status': 'already_current',
                    'existing_rows': existing_rows,
                    'new_rows': 0,
                    'last_date': last_date
                }
            else:
                # Рассчитываем период для догрузки
                start_date = last_dt + timedelta(days=1)  # Начинаем со следующего дня
                end_date = datetime.now()
                
                days_to_load = (end_date - start_date).days
                if days_to_load <= 0:
                    logger.info(f"Для {symbol} нет новых данных для загрузки")
                    return {
                        'status': 'no_new_data',
                        'existing_rows': existing_rows,
                        'new_rows': 0,
                        'last_date': last_date
                    }
                
                logger.info(f"Нужно догрузить {days_to_load} дней для {symbol} с {start_date.date()} по {end_date.date()}")
                
                # Загружаем только новые данные
                all_data_points = []
                chunks_needed = (days_to_load // MAX_POINTS_PER_REQUEST) + 1
                
                for chunk in range(chunks_needed):
                    chunk_start = start_date + timedelta(days=chunk * MAX_POINTS_PER_REQUEST)
                    chunk_end = min(start_date + timedelta(days=(chunk + 1) * MAX_POINTS_PER_REQUEST - 1), end_date)
                    
                    rate_limiter.wait_if_needed()
                    data = fetch_historical_chunk(
                        symbol,
                        chunk_start.strftime('%Y-%m-%d'),
                        chunk_end.strftime('%Y-%m-%d')
                    )
                    
                    if data and 'values' in data:
                        values = data['values']
                        values.reverse()  # API возвращает от новых к старым
                        all_data_points.extend(values)
                        logger.info(f"Чанк {chunk+1}/{chunks_needed} для {symbol} загружен: {len(values)} записей")
                    else:
                        logger.warning(f"Не удалось загрузить чанк {chunk+1} для {symbol}")
                    
                    if chunk < chunks_needed - 1:
                        time.sleep(0.5)
                
                # Сохраняем догруженные данные
                if all_data_points:
                    new_rows = save_to_csv(symbol, all_data_points)
                    logger.info(f"Догружено для {symbol}: {len(all_data_points)} записей, {new_rows} новых")
                    return {
                        'status': 'incremental_update',
                        'existing_rows': existing_rows,
                        'new_rows': new_rows,
                        'last_date': latest_available_date
                    }
                else:
                    logger.error(f"Не удалось догрузить данные для {symbol}")
                    return {
                        'status': 'incremental_failed',
                        'existing_rows': existing_rows,
                        'new_rows': 0,
                        'last_date': last_date
                    }
        
        else:
            logger.warning(f"Не удалось проверить актуальность данных для {symbol}, пропускаем")
            return {
                'status': 'check_failed',
                'existing_rows': existing_rows,
                'new_rows': 0,
                'last_date': last_date
            }
    
    else:
        # Полная загрузка (либо файла нет, либо force_reload=True)
        logger.info(f"Начинаем полную загрузку для {symbol}")
        
        # 1. Определяем самую раннюю дату
        rate_limiter.wait_if_needed()
        earliest_date = get_earliest_timestamp(symbol)
        start_date = datetime.strptime(earliest_date, '%Y-%m-%d')
        end_date = datetime.now()

        # 2. Рассчитываем количество необходимых чанков
        total_days = (end_date - start_date).days
        chunks_needed = (total_days // MAX_POINTS_PER_REQUEST) + 1
        logger.info(f"Для {symbol} потребуется {chunks_needed} чанков ({total_days} дней)")

        all_data_points = []
        # 3. Загружаем данные по чанкам
        for chunk in range(chunks_needed):
            chunk_start = start_date + timedelta(days=chunk * MAX_POINTS_PER_REQUEST)
            chunk_end = min(start_date + timedelta(days=(chunk + 1) * MAX_POINTS_PER_REQUEST - 1), end_date)

            rate_limiter.wait_if_needed()
            data = fetch_historical_chunk(
                symbol,
                chunk_start.strftime('%Y-%m-%d'),
                chunk_end.strftime('%Y-%m-%d')
            )

            if data and 'values' in data:
                values = data['values']
                values.reverse()  # API возвращает от новых к старым
                all_data_points.extend(values)
                logger.info(f"Чанк {chunk+1}/{chunks_needed} для {symbol} загружен: {len(values)} записей")
            else:
                logger.warning(f"Не удалось загрузить чанк {chunk+1} для {symbol}")

            if chunk < chunks_needed - 1:
                time.sleep(0.5)

        # 4. Сохраняем все данные в CSV
        if all_data_points:
            new_rows = save_to_csv(symbol, all_data_points)
            logger.info(f"Завершено для {symbol}. Всего обработано {len(all_data_points)} загруженных записей, {new_rows} новых.")
            return {
                'status': 'full_load',
                'existing_rows': 0,
                'new_rows': new_rows,
                'last_date': all_data_points[-1]['datetime'] if all_data_points else None
            }
        else:
            logger.error(f"Не удалось загрузить данные для {symbol}.")
            return {
                'status': 'failed',
                'existing_rows': 0,
                'new_rows': 0,
                'last_date': None
            }

def main():
    """
    Главная функция, которая загружает историю для всех пар.
    """
    # Загружаем список пар из конфигурационного файла
    currency_pairs = load_currency_config()
    
    if not currency_pairs:
        logger.error("Не удалось загрузить список валютных пар. Завершение.")
        return
    
    logger.info(f"Корень проекта: {PROJECT_ROOT}")
    logger.info(f"Начинаю первоначальную загрузку истории для {len(currency_pairs)} пар.")
    logger.info(f"Рабочий лимит: {SAFE_REQUESTS_PER_MINUTE} запросов в минуту.")
    logger.info(f"Логи будут сохранены в: {LOG_FILE}")
    logger.info(f"Каталог данных: {DATA_DIR}")

    rate_limiter = RateLimiter(SAFE_REQUESTS_PER_MINUTE)
    
    # Статистика
    stats = {
        'already_current': 0,
        'no_new_data': 0,
        'incremental_update': 0,
        'full_load': 0,
        'failed': 0,
        'check_failed': 0,
        'incremental_failed': 0,
        'total_new_rows': 0,
        'total_existing_rows': 0
    }
    
    results = {}

    for idx, pair in enumerate(currency_pairs, 1):
        logger.info(f"Обработка пары {idx}/{len(currency_pairs)}: {pair}")
        
        try:
            result = load_pair_history(pair, rate_limiter, force_reload=False)
            results[pair] = result
            
            # Обновляем статистику
            stats[result['status']] += 1
            stats['total_new_rows'] += result.get('new_rows', 0)
            stats['total_existing_rows'] += result.get('existing_rows', 0)
            
        except Exception as e:
            logger.error(f"Критическая ошибка при обработке {pair}: {e}")
            results[pair] = {'status': 'exception', 'error': str(e)}
            stats['failed'] += 1

        # Пауза между парами для распределения нагрузки
        if idx < len(currency_pairs):
            time.sleep(1)

    # Итоговый отчет
    logger.info("="*50)
    logger.info("ЗАГРУЗКА ЗАВЕРШЕНА")
    logger.info(f"Всего обработано пар: {len(currency_pairs)}")
    logger.info(f"Всего запросов к API: {rate_limiter.get_total_requests()}")
    logger.info("")
    logger.info("=== СТАТИСТИКА ===")
    logger.info(f"Уже актуальны: {stats['already_current']} пар")
    logger.info(f"Нет новых данных: {stats['no_new_data']} пар")
    logger.info(f"Догружены (инкрементально): {stats['incremental_update']} пар")
    logger.info(f"Полностью загружены: {stats['full_load']} пар")
    logger.info(f"Проверка не удалась: {stats['check_failed']} пар")
    logger.info(f"Догрузка не удалась: {stats['incremental_failed']} пар")
    logger.info(f"Не удалось загрузить: {stats['failed']} пар")
    logger.info("")
    logger.info(f"Всего существующих записей: {stats['total_existing_rows']}")
    logger.info(f"Всего новых записей: {stats['total_new_rows']}")
    logger.info(f"Итоговый лог: {LOG_FILE}")
    logger.info(f"Данные сохранены в: {DATA_DIR}")
    
    # Создаем сводный отчет
    create_summary_report(stats, results, rate_limiter.get_total_requests())
    
def create_summary_report(stats, results, total_requests):
    """
    Создает JSON отчет о результате загрузки.
    """
    report_file = os.path.join(LOG_DIR, f'load_summary_{datetime.now().strftime("%Y%m%d_%H%M")}.json')
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "project_root": PROJECT_ROOT,
        "total_pairs": len(results),
        "total_api_requests": total_requests,
        "statistics": stats,
        "results_by_pair": results,
        "data_directory": DATA_DIR,
        "metadata_directory": METADATA_DIR,
        "api_settings": {
            "requests_per_minute_limit": REQUESTS_PER_MINUTE_LIMIT,
            "safe_requests_per_minute": SAFE_REQUESTS_PER_MINUTE,
            "max_points_per_request": MAX_POINTS_PER_REQUEST,
            "interval": INTERVAL
        }
    }
    
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info(f"Сводный отчет сохранен: {report_file}")
    except Exception as e:
        logger.error(f"Ошибка сохранения отчета: {e}")

if __name__ == '__main__':
    main()
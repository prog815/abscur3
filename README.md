
# AbsCur3: Центральный репозиторий исторических валютных данных

[![GitHub Actions](https://img.shields.io/badge/Status-Active-success)](https://github.com/prog815/abscur3)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Total Pairs](https://img.shields.io/badge/Pairs-287-orange)](config/currencies.py)
[![Total Currencies](https://img.shields.io/badge/Currencies-153-blue)](data/analytics/currencies_list.txt)

**AbsCur3** — это open-source проект, предоставляющий полные исторические OHLC-данные по 287 валютным парам (34 мажорных, 107 минорных, 146 экзотических) с глубиной до 20+ лет. Все данные хранятся в структурированном виде и доступны бесплатно для анализа, исследований и обучения.

## 📊 Что внутри?

### Ключевые показатели:
- **287 валютных пар** (34 мажорных, 107 минорных, 146 экзотических)
- **153 уникальные валюты** из разных стран мира
- **Глубина истории:** до 37+ лет (с 1979 года для некоторых пар)
- **Формат данных:** дневные OHLC (Open, High, Low, Close)
- **Объём данных:** ~1M+ строк исторических котировок
- **Структура:** Единый граф связей с плотностью 0.0185
- **Частота обновления:** Инкрементальная загрузка при запуске

### 🎯 Основные возможности:
- ✅ **Прямой доступ** к данным через GitHub
- ✅ **Структурированный формат** CSV с сортировкой по дате
- ✅ **Гарантия качества** (дедупликация, валидация, сортировка)
- ✅ **Аналитика графа** валютных связей
- ✅ **Автоматическая загрузка** с контролем лимитов API
- ✅ **Открытый код** и конфигурация

## 🚀 Быстрый старт

### Доступ к данным (без установки):
```python
import pandas as pd

# Загрузить данные EUR/USD прямо из репозитория
eurusd = pd.read_csv('https://raw.githubusercontent.com/prog815/abscur3/main/data/raw/twelve_data/pairs/EURUSD.csv')
print(f"Загружено {len(eurusd)} строк исторических данных")
print(f"Диапазон дат: {eurusd['datetime'].min()} - {eurusd['datetime'].max()}")
```

### Просмотр доступных пар:
```python
import requests
import json

# Получить список всех пар
response = requests.get('https://raw.githubusercontent.com/prog815/abscur3/main/config/currencies.py')
# Или используйте встроенные функции из конфигурации:
from config.currencies import ALL_SYMBOLS, get_major_pairs, get_minor_pairs, get_exotic_pairs

print(f"Всего пар: {len(ALL_SYMBOLS)}")
print(f"Мажорные: {len(get_major_pairs())}")
print(f"Минорные: {len(get_minor_pairs())}")
print(f"Экзотические: {len(get_exotic_pairs())}")
```

### Анализ нескольких пар:
```python
import pandas as pd
import matplotlib.pyplot as plt

# Загрузка данных для сравнения
pairs = ['EURUSD', 'GBPUSD', 'USDJPY']
data = {}

for pair in pairs:
    data[pair] = pd.read_csv(f'https://raw.githubusercontent.com/prog815/abscur3/main/data/raw/twelve_data/pairs/{pair}.csv', 
                             parse_dates=['datetime'], index_col='datetime')
    data[pair]['returns'] = data[pair]['close'].pct_change()

# Визуализация корреляции
returns_df = pd.DataFrame({pair: data[pair]['returns'] for pair in pairs})
correlation_matrix = returns_df.corr()
print("Корреляция доходностей:")
print(correlation_matrix)
```

## 🏗️ Архитектура проекта

### Структура репозитория:
```
abscur3/
├── config/
│   └── currencies.py                   # Конфигурация 287 пар (34 мажорных, 107 минорных, 146 экзотических)
├── data/
│   ├── raw/twelve_data/
│   │   ├── pairs/                      # 287 CSV файлов с историческими данными
│   │   │   ├── EURUSD.csv             # Пример: мажорная пара (1979-12-24 - сегодня)
│   │   │   ├── AUDCAD.csv             # Пример: минорная пара (1979-12-24 - сегодня)
│   │   │   ├── USDAED.csv             # Пример: экзотическая пара (1990-03-07 - сегодня)
│   │   │   └── ... (284 файла)        # Все файлы: <ВАЛЮТА1><ВАЛЮТА2>.csv
│   │   └── metadata/
│   │       └── earliest_dates.json    # Кэш самых ранних доступных дат для каждой пары
│   ├── analytics/                      # Аналитические данные и граф связей
│   │   ├── currency_adjacency.csv     # Матрица смежности валют
│   │   ├── currency_centrality.csv    # Метрики центральности
│   │   ├── currency_pairs_full.csv    # Полный список пар с метаданными
│   │   ├── currencies_list.txt        # Список 153 уникальных валют
│   │   └── graph_statistics.json      # Статистика графа (плотность, связанность и т.д.)
│   └── research_results/              # Результаты исследований различных API
├── scripts/
│   ├── initial_load/                   # Скрипты первоначальной загрузки
│   │   ├── historical_loader.py       # Основной загрузчик данных с rate limiting
│   │   └── logs/                      # Логи выполнения загрузок
│   ├── research/                      # Исследовательские скрипты
│   │   ├── currencies.py              # Вспомогательные функции
│   │   ├── twelve_data/               # Тесты Twelve Data API
│   │   ├── ecb/                       # Тесты ECB API
│   │   ├── exchangerate_api/          # Тесты ExchangeRate API
│   │   └── frankfurter/               # Тесты Frankfurter.app
│   └── analysis/
│       └── graph_analysis.py          # Анализ графа валютных связей
├── reports/
│   └── graph_analysis_report.txt      # Текстовый отчет анализа графа
├── requirements.txt                    # Зависимости Python
└── README.md                          # Эта документация
```

### Формат данных:
Каждый CSV файл содержит 5 колонок и отсортирован по возрастанию даты:
```csv
datetime,open,high,low,close
2007-01-03,0.90120,0.90120,0.88560,0.88560
2007-01-04,0.88560,0.88560,0.88560,0.88560
2026-01-02,0.67210,0.67450,0.66830,0.67120
```

### Глубина истории по группам:
| Группа | Количество | Пример глубины | Ранние даты |
|--------|------------|----------------|-------------|
| **Мажорные** | 34 пар | До 37+ лет | USD/JPY: 1988-03-03, AUD/USD: 1979-12-24 |
| **Минорные** | 107 пар | 15-30 лет | AUD/CAD: 1979-12-24, USD/AFN: 1999-02-17 |
| **Экзотические** | 146 пар | 10-25 лет | USD/AED: 1990-03-07, EUR/AZN: 2001-05-07 |

**Полный список самых ранних дат:** [`data/raw/twelve_data/metadata/earliest_dates.json`](data/raw/twelve_data/metadata/earliest_dates.json)

## 📈 Примеры использования

### Финансовый анализ:
```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def analyze_pair(pair_symbol):
    """Полный анализ валютной пары"""
    # Загрузка данных
    df = pd.read_csv(f'https://raw.githubusercontent.com/prog815/abscur3/main/data/raw/twelve_data/pairs/{pair_symbol}.csv',
                     parse_dates=['datetime'], index_col='datetime')
    
    # Базовые расчеты
    df['returns'] = df['close'].pct_change()
    df['volatility'] = df['returns'].rolling(window=30).std() * np.sqrt(252)
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    
    # Статистика
    stats = {
        'start_date': df.index.min(),
        'end_date': df.index.max(),
        'total_days': len(df),
        'mean_return': df['returns'].mean(),
        'annual_volatility': df['volatility'].iloc[-1] if not df['volatility'].isna().all() else None,
        'sharpe_ratio': df['returns'].mean() / df['returns'].std() * np.sqrt(252) if df['returns'].std() > 0 else None
    }
    
    return df, stats

# Анализ EUR/USD
eurusd_df, eurusd_stats = analyze_pair('EURUSD')
print(f"EUR/USD анализ:")
for key, value in eurusd_stats.items():
    print(f"  {key}: {value}")
```

### Сравнительный анализ:
```python
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Сравнение мажорных пар
major_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD']
data = {}

for pair in major_pairs:
    df = pd.read_csv(f'https://raw.githubusercontent.com/prog815/abscur3/main/data/raw/twelve_data/pairs/{pair}.csv',
                     parse_dates=['datetime'], index_col='datetime')
    data[pair] = df['close'].pct_change().dropna()

# Создание DataFrame для корреляционного анализа
returns_df = pd.DataFrame(data)

# Визуализация
plt.figure(figsize=(12, 8))

# 1. Матрица корреляций
plt.subplot(2, 2, 1)
sns.heatmap(returns_df.corr(), annot=True, cmap='coolwarm', center=0)
plt.title('Корреляция мажорных пар')

# 2. Кумулятивная доходность
plt.subplot(2, 2, 2)
cumulative_returns = (1 + returns_df).cumprod()
cumulative_returns.plot(ax=plt.gca())
plt.title('Кумулятивная доходность')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

# 3. Распределение доходностей
plt.subplot(2, 2, 3)
for pair in major_pairs[:3]:  # Первые 3 пары для наглядности
    sns.kdeplot(returns_df[pair].dropna(), label=pair)
plt.title('Распределение доходностей')
plt.xlabel('Дневная доходность')

plt.tight_layout()
plt.show()
```

### Исследование графа валютных связей:
```python
import json
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

# Загрузка аналитики графа
with open('data/analytics/graph_statistics.json', 'r') as f:
    graph_stats = json.load(f)

print("Статистика графа валютных связей:")
print(f"Всего пар: {graph_stats['total_pairs']}")
print(f"Уникальных валют: {graph_stats['total_currencies']}")
print(f"Плотность графа: {graph_stats['graph_density']:.4f}")
print(f"Средняя степень связности: {graph_stats['average_degree']:.2f}")
print(f"Компоненты связности: {graph_stats['connected_components']}")

# Загрузка матрицы смежности
adjacency_df = pd.read_csv('data/analytics/currency_adjacency.csv', index_col=0)

# Построение простого графа
G = nx.Graph()
for currency in adjacency_df.index:
    for other_currency in adjacency_df.columns:
        if adjacency_df.loc[currency, other_currency] == 1:
            G.add_edge(currency, other_currency)

# Визуализация
plt.figure(figsize=(15, 10))
pos = nx.spring_layout(G, k=0.5, iterations=50)
nx.draw_networkx_nodes(G, pos, node_size=50, node_color='lightblue')
nx.draw_networkx_edges(G, pos, alpha=0.3)
nx.draw_networkx_labels(G, pos, font_size=8)
plt.title(f"Граф валютных связей ({len(G.nodes())} валют, {len(G.edges())} связей)")
plt.axis('off')
plt.show()
```

## ⚙️ Технические детали

### Источник данных:
- **Основной API:** [Twelve Data](https://twelvedata.com) (бесплатный тариф Basic)
- **Лимиты:** 8 запросов в минуту, 800 запросов в день
- **Максимальная глубина:** 5000 точек данных за запрос
- **Формат ответа:** JSON с OHLC-данными

### Стратегия загрузки:
1. **Rate Limiting:** Класс `RateLimiter` контролирует 7 запросов в минуту (из 8 доступных)
2. **Чанкование:** Разбивка длинных периодов на отрезки по 5000 дней
3. **Инкрементальная загрузка:** Проверка существующих данных и догрузка только новых
4. **Гарантия качества:** Автоматическая сортировка, дедупликация и валидация

### Ключевой код:
```python
# Пример: Rate Limiter из historical_loader.py
class RateLimiter:
    def __init__(self, max_per_minute):
        self.max_per_minute = max_per_minute
        self.request_timestamps = []
    
    def wait_if_needed(self):
        now = time.time()
        minute_ago = now - 60
        self.request_timestamps = [ts for ts in self.request_timestamps if ts > minute_ago]
        
        if len(self.request_timestamps) >= self.max_per_minute:
            sleep_time = 60 - (now - self.request_timestamps[0]) + 1
            time.sleep(sleep_time)
        
        self.request_timestamps.append(now)
```

## 🔧 Локальная установка

### 1. Клонирование репозитория:
```bash
git clone https://github.com/prog815/abscur3.git
cd abscur3
```

### 2. Установка зависимостей:
```bash
pip install -r requirements.txt
```

Зависимости проекта:
- `pandas>=2.3.3` - обработка данных
- `requests>=2.32.5` - HTTP-запросы к API
- `matplotlib>=3.10.8` - визуализация
- `networkx>=3.4.2` - анализ графов
- `python-dotenv>=1.2.1` - управление переменными окружения

### 3. Настройка API ключа:
```bash
cp .env.example .env
# Отредактируйте .env, добавив ваш API ключ Twelve Data:
# TWELVE_DATA_API_KEY=ваш_ключ_здесь
```

### 4. Запуск загрузки данных:
```bash
# Загрузка всех данных (может занять несколько часов)
python scripts/initial_load/historical_loader.py

# Просмотр логов
tail -f scripts/initial_load/logs/initial_load_*.log
```

### 5. Анализ графа валютных связей:
```bash
python scripts/analysis/graph_analysis.py
```

## 📚 Документация

### Структура данных:
- **Каждая пара** хранится в отдельном CSV файле: `<ВАЛЮТА1><ВАЛЮТА2>.csv`
- **Формат:** datetime (YYYY-MM-DD), open, high, low, close
- **Сортировка:** По возрастанию даты
- **Дедупликация:** Автоматическое удаление дублей с приоритетом новых данных

### Категории пар:

#### Мажорные (34 пары):
- Пары с высокой ликвидностью и объемом торгов
- Примеры: EUR/USD, USD/JPY, GBP/USD, AUD/USD
- Глубина: 20-37+ лет истории

#### Минорные (107 пар):
- Пары без USD, но с основными валютами
- Примеры: EUR/GBP, AUD/CAD, NZD/JPY
- Глубина: 15-30+ лет истории

#### Экзотические (146 пар):
- Пары с валютами развивающихся стран
- Примеры: USD/AED, EUR/AZN, USD/KZT
- Глубина: 10-25+ лет истории

### Граф валютных связей:
```
Ключевые метрики:
- Всего валют: 153
- Всего пар: 287
- Плотность графа: 0.0185 (разреженный)
- Средняя степень: 2.81 связи на валюту
- Компоненты связности: 1 (полносвязный граф)

Топ-5 центральных валют:
1. USD - абсолютный хаб (связан с большинством валют)
2. EUR - европейский центр
3. JPY - азиатский центр
4. GBP - британский фунт
5. AUD - австралийский доллар
```

## 🎯 Варианты использования

### Для исследователей:
- Анализ исторических закономерностей
- Тестирование торговых стратегий
- Исследование корреляций между валютами
- Анализ волатильности и рисков

### Для разработчиков:
- Интеграция в финансовые приложения
- Создание дашбордов и аналитических инструментов
- Разработка алгоритмов машинного обучения
- Бэктестинг торговых систем

### Для студентов и преподавателей:
- Образовательные проекты по финансам
- Практикумы по анализу временных рядов
- Исследования в области экономики
- Примеры работы с реальными финансовыми данными

## ⚠️ Ограничения и отказ от ответственности

### Важно:
1. **Только для образовательных и исследовательских целей**
2. **Не для принятия торговых или инвестиционных решений**
3. **Данные предоставляются "как есть" без гарантий**
4. **Проверяйте актуальность данных перед использованием**

### Известные ограничения:
- Бесплатный тариф Twelve Data имеет лимиты (8 запросов/мин)
- Некоторые экзотические пары имеют меньшую глубину истории
- Данные могут обновляться с задержкой
- Выходные и праздничные дни могут отсутствовать в данных

### Рекомендации:
- Всегда проверяйте качество данных перед использованием
- Используйте несколько источников для критически важных приложений
- Реализуйте механизмы обработки ошибок и восстановления
- Соблюдайте лимиты API при самостоятельной загрузке данных

## 🔄 Обновление данных

### Автоматическая загрузка:
```bash
# Скрипт автоматически проверяет и догружает новые данные
python scripts/initial_load/historical_loader.py
```

### Ручное обновление:
1. Убедитесь, что API ключ актуален
2. Запустите скрипт загрузки
3. Проверьте логи на наличие ошибок
4. При необходимости обновите конфигурацию пар

## 🤝 Вклад в проект

### Как помочь:
1. **Отчеты об ошибках:** Создавайте issues с описанием проблемы
2. **Улучшения кода:** Pull requests с оптимизациями и новыми функциями
3. **Тестирование:** Помощь с тестированием на разных платформах
4. **Идеи:** Предложения по улучшению архитектуры или функционала

### Области для улучшения:
- Добавление новых источников данных (ECB, Alpha Vantage и др.)
- Реализация ежедневного автоматического обновления через GitHub Actions
- Создание веб-интерфейса для просмотра данных
- Добавление интерактивных графиков и аналитических инструментов
- Поддержка дополнительных интервалов (часовые, недельные данные)
- Улучшение производительности загрузки данных

## 📄 Лицензия

Проект распространяется под лицензией MIT. 

```
MIT License

Copyright (c) 2026 prog815

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

## 👤 Автор и контакты

**prog815**
- GitHub: [@prog815](https://github.com/prog815)
- Проект: [AbsCur3](https://github.com/prog815/abscur3)

### Благодарности:
- [Twelve Data](https://twelvedata.com) за бесплатный доступ к API
- Сообществу open-source за инструменты и библиотеки
- Всем, кто вносит вклад в развитие проекта

---

**⭐ Если проект полезен для вас, поставьте звезду на GitHub!**

**🔔 Следите за обновлениями:** Проект активно развивается, планируется добавление новых функций и источников данных.

**💬 Вопросы и предложения:** Создавайте issues в репозитории или свяжитесь с автором.

---

*Последнее обновление: Январь 2026*  
*Данные актуальны на: Январь 2026*  
*Статус проекта: Активно развивается*
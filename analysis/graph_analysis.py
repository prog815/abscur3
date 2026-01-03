#!/usr/bin/env python3
"""
Скрипт для анализа графа валютных пар проекта AbsCur3.
Запускать ИЗ КОРНЯ ПРОЕКТА: python analysis/graph_analysis.py
"""

import sys
import os
import json
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import datetime

# ВСЕ ПУТИ ОТНОСИТЕЛЬНО КОРНЯ ПРОЕКТА
# Предполагается, что скрипт запускается из корня

def setup_directories():
    """Создает необходимые директории в корне проекта."""
    directories = [
        'data/visualizations',
        'data/analytics',
        'reports'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Создана директория: {directory}")
    
    return directories

def load_currency_config():
    """Загружает конфигурацию валютных пар из config/currencies.py."""
    try:
        # Проверяем, что находимся в правильном месте
        if not os.path.exists('config/currencies.py'):
            print("⚠ Файл config/currencies.py не найден в текущей директории")
            print("⚠ Запускайте скрипт из корня проекта: python analysis/graph_analysis.py")
            return []
        
        # Импортируем напрямую
        sys.path.insert(0, '.')
        from config.currencies import CURRENCY_PAIRS
        
        print(f"✓ Конфигурация загружена из config/currencies.py")
        print(f"✓ Загружено {len(CURRENCY_PAIRS)} валютных пар")
        return CURRENCY_PAIRS
        
    except ImportError as e:
        print(f"✗ Ошибка импорта: {e}")
        return []
    except Exception as e:
        print(f"✗ Неожиданная ошибка: {e}")
        return []

def create_currency_graph(currency_pairs):
    """Создает граф на основе списка валютных пар."""
    print("\n" + "="*60)
    print("ПОСТРОЕНИЕ ГРАФА ВАЛЮТНЫХ ПАР")
    print("="*60)
    
    if not currency_pairs:
        print("✗ Нет данных для построения графа")
        return None, None
    
    # Преобразуем данные
    processed_pairs = []
    for symbol, group, base_name, quote_name in currency_pairs:
        try:
            base, quote = symbol.split('/')
            processed_pairs.append({
                'symbol': symbol,
                'base': base,
                'quote': quote,
                'group': group,
                'base_name': base_name,
                'quote_name': quote_name
            })
        except ValueError:
            print(f"⚠ Пропущена некорректная пара: {symbol}")
    
    # Создаем граф
    G = nx.Graph()
    
    for pair in processed_pairs:
        G.add_edge(pair['base'], pair['quote'], 
                   symbol=pair['symbol'], 
                   group=pair['group'])
    
    # Базовая статистика
    print(f"Уникальных валют: {G.number_of_nodes()}")
    print(f"Связей (валютных пар): {G.number_of_edges()}")
    print(f"Плотность графа: {nx.density(G):.4f}")
    
    # Сохраняем список валют
    currencies_list = sorted(list(G.nodes()))
    with open('data/analytics/currencies_list.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(currencies_list))
    print(f"✓ Список валют сохранен: data/analytics/currencies_list.txt")
    
    return G, processed_pairs

def analyze_graph_centrality(G):
    """Анализирует центральность валют в графе."""
    if G is None:
        return pd.DataFrame()
    
    print("\n" + "="*60)
    print("АНАЛИЗ ЦЕНТРАЛЬНОСТИ ВАЛЮТ")
    print("="*60)
    
    # Вычисляем метрики центральности
    degree_centrality = nx.degree_centrality(G)
    betweenness_centrality = nx.betweenness_centrality(G)
    closeness_centrality = nx.closeness_centrality(G)
    
    # Создаем DataFrame с результатами
    centrality_data = []
    for currency in G.nodes():
        centrality_data.append({
            'Валюта': currency,
            'Степень': G.degree(currency),
            'Центральность_степени': degree_centrality[currency],
            'Посредничество': betweenness_centrality[currency],
            'Близость': closeness_centrality[currency]
        })
    
    centrality_df = pd.DataFrame(centrality_data)
    centrality_df = centrality_df.sort_values('Степень', ascending=False).reset_index(drop=True)
    
    # Выводим топ-10 валют
    print("\nТОП-10 ВАЛЮТ ПО СВЯЗНОСТИ:")
    print(centrality_df.head(10).to_string(index=False))
    
    return centrality_df

def visualize_graph(G, processed_pairs):
    """Создает визуализации графа."""
    if G is None:
        return []
    
    print("\n" + "="*60)
    print("СОЗДАНИЕ ВИЗУАЛИЗАЦИЙ")
    print("="*60)
    
    # 1. ОСНОВНОЙ ГРАФ
    print("Создаю основной граф...")
    plt.figure(figsize=(20, 16))
    
    # Используем spring layout для позиционирования
    pos = nx.spring_layout(G, k=1.2, iterations=100, seed=42)
    
    # Определяем размер узлов по степени связности
    node_sizes = [800 + G.degree(node) * 120 for node in G.nodes()]
    
    # Определяем цвет узлов: красный для основных валют
    major_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD', 'RUB']
    node_colors = []
    for node in G.nodes():
        if node in major_currencies:
            node_colors.append('#ff6b6b')  # Красный
        elif G.degree(node) >= 5:
            node_colors.append('#4ecdc4')   # Бирюзовый
        else:
            node_colors.append('#a0aec0')   # Серый
    
    # Определяем стиль ребер
    edge_colors = []
    edge_widths = []
    
    for u, v, data in G.edges(data=True):
        if data['group'] == 'Major':
            edge_colors.append('#e53e3e')  # Красный для Major
            edge_widths.append(3.0)
        else:
            edge_colors.append('#cbd5e0')  # Серый для Minor
            edge_widths.append(1.0)
    
    # Рисуем граф
    nx.draw_networkx_nodes(G, pos, 
                          node_size=node_sizes,
                          node_color=node_colors,
                          alpha=0.9,
                          edgecolors='#2d3748',
                          linewidths=2)
    
    nx.draw_networkx_edges(G, pos,
                          edge_color=edge_colors,
                          width=edge_widths,
                          alpha=0.7)
    
    # Подписываем только важные узлы
    labels = {}
    for node in G.nodes():
        if G.degree(node) >= 3 or node in major_currencies:
            labels[node] = node
    
    nx.draw_networkx_labels(G, pos, labels, 
                           font_size=11, 
                           font_weight='bold',
                           font_family='DejaVu Sans')
    
    # Заголовок и легенда
    plt.title(f'ГРАФ ВАЛЮТНЫХ ПАР ABSCUR3\n{G.number_of_nodes()} валют, {G.number_of_edges()} пар',
              fontsize=24, fontweight='bold', pad=20)
    
    # Создаем легенду
    legend_elements = [
        mpatches.Patch(color='#ff6b6b', label='Основные валюты (USD, EUR, RUB и др.)'),
        mpatches.Patch(color='#4ecdc4', label='Валюты со средней связностью'),
        mpatches.Patch(color='#a0aec0', label='Прочие валюты'),
        mpatches.Patch(color='#e53e3e', label='Мажорные пары (Major)'),
        mpatches.Patch(color='#cbd5e0', label='Минорные пары (Minor)')
    ]
    
    plt.legend(handles=legend_elements, 
               loc='upper right', 
               fontsize=12,
               framealpha=0.9)
    
    plt.axis('off')
    plt.tight_layout()
    
    # Сохраняем основной граф
    plt.savefig('data/visualizations/currency_graph_main.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Основной граф сохранен: data/visualizations/currency_graph_main.png")
    
    # 2. ГРАФ ТОЛЬКО МАЖОРНЫХ ПАР
    print("Создаю граф мажорных пар...")
    major_edges = [(u, v) for u, v, d in G.edges(data=True) if d['group'] == 'Major']
    G_major = nx.Graph(major_edges)
    
    if G_major.number_of_nodes() > 0:
        plt.figure(figsize=(14, 10))
        pos_major = nx.spring_layout(G_major, seed=42)
        node_sizes_major = [1200 + G.degree(node) * 150 for node in G_major.nodes()]
        
        nx.draw_networkx_nodes(G_major, pos_major,
                              node_size=node_sizes_major,
                              node_color='#ff6b6b',
                              alpha=0.9,
                              edgecolors='#c53030',
                              linewidths=2)
        
        nx.draw_networkx_edges(G_major, pos_major,
                              edge_color='#e53e3e',
                              width=3.0,
                              alpha=0.8)
        
        nx.draw_networkx_labels(G_major, pos_major,
                               font_size=12,
                               font_weight='bold')
        
        plt.title(f'ГРАФ МАЖОРНЫХ ВАЛЮТНЫХ ПАР\n{G_major.number_of_nodes()} валют, {G_major.number_of_edges()} пар',
                  fontsize=18, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        
        plt.savefig('data/visualizations/currency_graph_major_only.png', dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Граф мажорных пар сохранен: data/visualizations/currency_graph_major_only.png")
    
    # 3. ГИСТОГРАММА РАСПРЕДЕЛЕНИЯ СВЯЗЕЙ
    print("Создаю гистограмму распределения связей...")
    degrees = [G.degree(node) for node in G.nodes()]
    
    plt.figure(figsize=(12, 7))
    plt.hist(degrees, bins=20, color='#4299e1', edgecolor='#2b6cb0', alpha=0.7)
    plt.xlabel('Количество связей', fontsize=12)
    plt.ylabel('Количество валют', fontsize=12)
    plt.title('Распределение количества связей между валютами', fontsize=16, fontweight='bold')
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    
    plt.savefig('data/visualizations/degree_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Гистограмма сохранена: data/visualizations/degree_distribution.png")
    
    return [
        'data/visualizations/currency_graph_main.png',
        'data/visualizations/currency_graph_major_only.png',
        'data/visualizations/degree_distribution.png'
    ]

def export_analytics(G, processed_pairs, centrality_df):
    """Экспортирует аналитические данные в CSV и JSON."""
    if G is None:
        return []
    
    print("\n" + "="*60)
    print("ЭКСПОРТ АНАЛИТИЧЕСКИХ ДАННЫХ")
    print("="*60)
    
    # 1. Список всех пар
    pairs_df = pd.DataFrame(processed_pairs)
    pairs_df.to_csv('data/analytics/currency_pairs_full.csv', index=False, encoding='utf-8-sig')
    print(f"✓ Список пар сохранен: data/analytics/currency_pairs_full.csv")
    
    # 2. Метрики центральности
    centrality_df.to_csv('data/analytics/currency_centrality.csv', index=False, encoding='utf-8-sig')
    print(f"✓ Метрики центральности сохранены: data/analytics/currency_centrality.csv")
    
    # 3. Матрица смежности (какие валюты связаны)
    adjacency_data = []
    for u, v, data in G.edges(data=True):
        adjacency_data.append({
            'Валюта_1': u,
            'Валюта_2': v,
            'Пара': data['symbol'],
            'Тип': data['group']
        })
    
    adjacency_df = pd.DataFrame(adjacency_data)
    adjacency_df.to_csv('data/analytics/currency_adjacency.csv', index=False, encoding='utf-8-sig')
    print(f"✓ Матрица смежности сохранена: data/analytics/currency_adjacency.csv")
    
    # 4. Статистика по типам пар
    stats = {
        'total_pairs': len(processed_pairs),
        'total_currencies': G.number_of_nodes(),
        'major_pairs': len([p for p in processed_pairs if p['group'] == 'Major']),
        'minor_pairs': len([p for p in processed_pairs if p['group'] == 'Minor']),
        'graph_density': float(nx.density(G)),
        'average_degree': float(np.mean([d for _, d in G.degree()])),
        'connected_components': len(list(nx.connected_components(G))),
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open('data/analytics/graph_statistics.json', 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"✓ Статистика графа сохранена: data/analytics/graph_statistics.json")
    
    return [
        'data/analytics/currency_pairs_full.csv',
        'data/analytics/currency_centrality.csv',
        'data/analytics/currency_adjacency.csv',
        'data/analytics/graph_statistics.json'
    ]

def generate_report(G, processed_pairs, centrality_df):
    """Генерирует текстовый отчет."""
    if G is None:
        return None
    
    print("\n" + "="*60)
    print("ГЕНЕРАЦИЯ ОТЧЕТА")
    print("="*60)
    
    report_lines = [
        "=" * 80,
        "ОТЧЕТ ПО АНАЛИЗУ ГРАФА ВАЛЮТНЫХ ПАР ABSCUR3",
        "=" * 80,
        f"Дата генерации: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Скрипт: analysis/graph_analysis.py",
        "",
        "I. ОБЩАЯ СТАТИСТИКА",
        "-" * 40,
        f"• Всего пар в конфигурации: {len(processed_pairs)}",
        f"• Уникальных валют: {G.number_of_nodes()}",
        f"• Связей в графе: {G.number_of_edges()}",
        f"• Мажорных пар (Major): {len([p for p in processed_pairs if p['group'] == 'Major'])}",
        f"• Минорных пар (Minor): {len([p for p in processed_pairs if p['group'] == 'Minor'])}",
        f"• Плотность графа: {nx.density(G):.4f}",
        f"• Среднее количество связей на валюту: {np.mean([d for _, d in G.degree()]):.2f}",
        f"• Компонентов связности: {len(list(nx.connected_components(G)))}",
        "",
        "II. ТОП-10 ВАЛЮТ ПО ЦЕНТРАЛЬНОСТИ",
        "-" * 40,
    ]
    
    # Добавляем топ-10 валют
    for i, row in centrality_df.head(10).iterrows():
        report_lines.append(f"{i+1:2}. {row['Валюта']:5} - {int(row['Степень']):3} связей "
                           f"(центральность: {row['Центральность_степени']:.4f})")
    
    report_lines.extend([
        "",
        "III. АНАЛИЗ СВЯЗЕЙ КЛЮЧЕВЫХ ВАЛЮТ",
        "-" * 40,
    ])
    
    # Анализ ключевых валют
    key_currencies = ['USD', 'EUR', 'RUB', 'JPY', 'GBP']
    for currency in key_currencies:
        if currency in G.nodes():
            neighbors = list(G.neighbors(currency))
            major_count = sum(1 for n in neighbors 
                            if G[currency][n]['group'] == 'Major')
            
            report_lines.append(f"• {currency}: {len(neighbors)} связей "
                              f"({major_count} мажорных)")
    
    report_lines.extend([
        "",
        "IV. СОЗДАННЫЕ ФАЙЛЫ",
        "-" * 40,
        "ВИЗУАЛИЗАЦИИ:",
        "• data/visualizations/currency_graph_main.png - Основной граф",
        "• data/visualizations/currency_graph_major_only.png - Граф мажорных пар",
        "• data/visualizations/degree_distribution.png - Гистограмма распределения связей",
        "",
        "АНАЛИТИЧЕСКИЕ ДАННЫЕ:",
        "• data/analytics/currency_pairs_full.csv - Полный список пар",
        "• data/analytics/currency_centrality.csv - Метрики центральности валют",
        "• data/analytics/currency_adjacency.csv - Матрица смежности",
        "• data/analytics/graph_statistics.json - Статистика графа",
        "• data/analytics/currencies_list.txt - Список всех уникальных валют",
        "",
        "V. РЕКОМЕНДАЦИИ",
        "-" * 40,
        "1. Начать загрузку данных с наиболее центральных валют (USD, EUR, etc.)",
        "2. Проверить покрытие для валют с малым количеством связей",
        "3. Использовать мажорные пары для первоначальной валидации системы",
        "4. Рассмотреть добавление пар для изолированных валют",
        "",
        "=" * 80,
        "АНАЛИЗ ЗАВЕРШЕН УСПЕШНО!",
        "=" * 80
    ])
    
    # Сохраняем отчет
    with open('reports/graph_analysis_report.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"✓ Отчет сохранен: reports/graph_analysis_report.txt")
    
    # Выводим краткую информацию в консоль
    print("\n📋 КРАТКИЙ ОТЧЕТ:")
    print(f"   • Валют: {G.number_of_nodes()}")
    print(f"   • Пар: {len(processed_pairs)}")
    print(f"   • Наиболее связанная валюта: {centrality_df.iloc[0]['Валюта']} "
          f"({centrality_df.iloc[0]['Степень']} связей)")
    
    return 'reports/graph_analysis_report.txt'

def main():
    """Основная функция скрипта."""
    print("🚀 ЗАПУСК СКРИПТА АНАЛИЗА ГРАФА ВАЛЮТНЫХ ПАР")
    print("="*60)
    print("Запускайте из корня проекта: python analysis/graph_analysis.py")
    print("Текущая директория:", os.getcwd())
    
    try:
        # 1. Настройка директорий
        setup_directories()
        
        # 2. Загрузка конфигурации
        currency_pairs = load_currency_config()
        if not currency_pairs:
            print("✗ Не удалось загрузить данные. Завершение работы.")
            return 1
        
        # 3. Создание графа
        G, processed_pairs = create_currency_graph(currency_pairs)
        
        # 4. Анализ центральности
        centrality_df = analyze_graph_centrality(G)
        
        # 5. Создание визуализаций
        visualization_files = visualize_graph(G, processed_pairs)
        
        # 6. Экспорт данных
        export_files = export_analytics(G, processed_pairs, centrality_df)
        
        # 7. Генерация отчета
        report_file = generate_report(G, processed_pairs, centrality_df)
        
        print("\n" + "="*60)
        print("✅ ВСЕ ЗАДАЧИ ВЫПОЛНЕНЫ УСПЕШНО!")
        print("="*60)
        print(f"\n📁 Созданы файлы:")
        print(f"   • Визуализации: {len(visualization_files)} файлов")
        print(f"   • Аналитика: {len(export_files) + 1} файлов")  # +1 для currencies_list.txt
        print(f"   • Отчет: 1 файл")
        print(f"\n📄 Основной отчет: {report_file}")
        print(f"📊 Главная визуализация: {visualization_files[0]}")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА ВЫПОЛНЕНИЯ: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
#!/usr/bin/env python3
"""
Детальный анализ логики арбитражного бота
"""

import asyncio
import logging
from config import SLIP_BY_DEPTH
from core.processor import process_depth
from core.matcher import _normalize, _extract_teams

# Настройка логирования
logging.basicConfig(level=logging.INFO)


def analyze_config():
    """Анализируем конфигурацию бота"""
    print("🔧 АНАЛИЗ КОНФИГУРАЦИИ")
    print("=" * 50)
    print(f"SLIP_BY_DEPTH: {SLIP_BY_DEPTH}")
    print("\nЛогика проскальзывания:")
    for depth, slip in sorted(SLIP_BY_DEPTH.items(), reverse=True):
        print(f"  - Глубина ≥ {depth}: проскальзывание {slip:.4f}")
    print()


def analyze_processor_logic():
    """Анализируем логику процессора"""
    print("⚙️ АНАЛИЗ ЛОГИКИ ПРОЦЕССОРА")
    print("=" * 50)

    # Тестируем граничные случаи
    test_cases = [
        (2000, 1800, "Очень высокая глубина"),
        (1000, 1000, "Точная граница 1000"),
        (999, 999, "Чуть ниже границы 1000"),
        (500, 500, "Точная граница 500"),
        (499, 499, "Чуть ниже границы 500"),
        (0, 0, "Точная граница 0"),
        (-100, -100, "Отрицательная глубина"),
    ]

    for pm_depth, sx_depth, description in test_cases:
        try:
            max_slip = asyncio.run(process_depth(pm_depth, sx_depth))
            print(
                f"  {description}: PM={pm_depth}, SX={sx_depth} → slippage={max_slip:.4f}"
            )
        except Exception as e:
            print(f"  {description}: PM={pm_depth}, SX={sx_depth} → ОШИБКА: {e}")
    print()


def analyze_matcher_logic():
    """Анализируем логику матчера"""
    print("🔍 АНАЛИЗ ЛОГИКИ МАТЧЕРА")
    print("=" * 50)

    # Тестируем нормализацию
    test_strings = [
        "Boston Celtics @ LA Clippers",
        "boston celtics @ la clippers",
        "Boston-Celtics @ LA-Clippers",
        "Boston Celtics at LA Clippers",
        "Simple Title",
    ]

    print("Нормализация строк:")
    for s in test_strings:
        normalized = _normalize(s)
        teams = _extract_teams(s)
        print(f"  '{s}' → '{normalized}' → teams: {teams}")
    print()


def analyze_error_handling():
    """Анализируем обработку ошибок"""
    print("🚨 АНАЛИЗ ОБРАБОТКИ ОШИБОК")
    print("=" * 50)

    # Тестируем различные сценарии ошибок
    error_cases = [
        (None, 100, "None для PM"),
        (100, None, "None для SX"),
        (float("inf"), 100, "Бесконечность для PM"),
        (100, float("-inf"), "Минус бесконечность для SX"),
        (0, 0, "Нулевая глубина"),
    ]

    for pm_depth, sx_depth, description in error_cases:
        try:
            max_slip = asyncio.run(process_depth(pm_depth, sx_depth))
            print(f"  {description}: slippage={max_slip:.4f}")
        except Exception as e:
            print(f"  {description}: ОШИБКА: {type(e).__name__}: {e}")
    print()


def analyze_performance():
    """Анализируем производительность"""
    print("⚡ АНАЛИЗ ПРОИЗВОДИТЕЛЬНОСТИ")
    print("=" * 50)

    import time

    # Тестируем скорость обработки
    test_depths = [(1000, 800)] * 1000

    start_time = time.time()
    for pm_depth, sx_depth in test_depths:
        asyncio.run(process_depth(pm_depth, sx_depth))
    end_time = time.time()

    total_time = end_time - start_time
    avg_time = total_time / len(test_depths)

    print(f"  Обработано {len(test_depths)} запросов за {total_time:.3f} сек")
    print(f"  Среднее время на запрос: {avg_time*1000:.3f} мс")
    print(f"  Пропускная способность: {len(test_depths)/total_time:.0f} запросов/сек")
    print()


def main():
    """Основная функция анализа"""
    print("🤖 ДЕТАЛЬНЫЙ АНАЛИЗ АРБИТРАЖНОГО БОТА")
    print("=" * 60)
    print()

    analyze_config()
    analyze_processor_logic()
    analyze_matcher_logic()
    analyze_error_handling()
    analyze_performance()

    print("✅ Анализ завершен!")


if __name__ == "__main__":
    main()

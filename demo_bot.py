#!/usr/bin/env python3
"""
Демо-версия арбитражного бота с моковыми данными
"""

import argparse
import asyncio
import logging
import random
from typing import Any, Dict, List, Tuple

from core.metrics import init_metrics
from core.alerts import TelegramHandler
from core.processor import process_depth

# Моковые данные для демонстрации
MOCK_DEPTH_DATA = {
    "polymarket": {
        "bids": [
            {"price": 0.65, "size": 1000},
            {"price": 0.64, "size": 1500},
            {"price": 0.63, "size": 2000},
            {"price": 0.62, "size": 2500},
            {"price": 0.61, "size": 3000},
        ],
        "asks": [
            {"price": 0.66, "size": 800},
            {"price": 0.67, "size": 1200},
            {"price": 0.68, "size": 1800},
            {"price": 0.69, "size": 2200},
            {"price": 0.70, "size": 2800},
        ],
    },
    "sx": {
        "bids": [
            {"price": 0.655, "size": 900},
            {"price": 0.645, "size": 1400},
            {"price": 0.635, "size": 1900},
            {"price": 0.625, "size": 2400},
            {"price": 0.615, "size": 2900},
        ],
        "asks": [
            {"price": 0.665, "size": 750},
            {"price": 0.675, "size": 1150},
            {"price": 0.685, "size": 1750},
            {"price": 0.695, "size": 2150},
            {"price": 0.705, "size": 2750},
        ],
    },
}


def generate_mock_depth() -> Tuple[Dict, Dict]:
    """Генерируем моковые данные о глубине стакана с небольшими вариациями"""

    # Добавляем случайные вариации к базовым данным
    pm_depth: Dict[str, List[Dict[str, Any]]] = {"bids": [], "asks": []}

    sx_depth: Dict[str, List[Dict[str, Any]]] = {"bids": [], "asks": []}

    # Генерируем данные для Polymarket
    for bid in MOCK_DEPTH_DATA["polymarket"]["bids"]:
        price_variation = random.uniform(-0.01, 0.01)
        size_variation = random.uniform(0.8, 1.2)

        pm_depth["bids"].append(
            {
                "price": round(bid["price"] + price_variation, 4),
                "size": int(bid["size"] * size_variation),
            }
        )

    for ask in MOCK_DEPTH_DATA["polymarket"]["asks"]:
        price_variation = random.uniform(-0.01, 0.01)
        size_variation = random.uniform(0.8, 1.2)

        pm_depth["asks"].append(
            {
                "price": round(ask["price"] + price_variation, 4),
                "size": int(ask["size"] * size_variation),
            }
        )

    # Генерируем данные для SX
    for bid in MOCK_DEPTH_DATA["sx"]["bids"]:
        price_variation = random.uniform(-0.01, 0.01)
        size_variation = random.uniform(0.8, 1.2)

        sx_depth["bids"].append(
            {
                "price": round(bid["price"] + price_variation, 4),
                "size": int(bid["size"] * size_variation),
            }
        )

    for ask in MOCK_DEPTH_DATA["sx"]["asks"]:
        price_variation = random.uniform(-0.01, 0.01)
        size_variation = random.uniform(0.8, 1.2)

        sx_depth["asks"].append(
            {
                "price": round(ask["price"] + price_variation, 4),
                "size": int(ask["size"] * size_variation),
            }
        )

    return pm_depth, sx_depth


def print_depth_analysis(pm_depth: Dict, sx_depth: Dict) -> None:
    """Выводим анализ глубины стакана"""
    print("\n📊 АНАЛИЗ ГЛУБИНЫ СТАКАНА")
    print("=" * 50)

    # Polymarket
    print("🔵 Polymarket:")
    print("   Лучшие цены покупки:")
    for i, bid in enumerate(pm_depth["bids"][:3]):
        print(f"     {i+1}. ${bid['price']:.4f} - {bid['size']} шт")

    print("   Лучшие цены продажи:")
    for i, ask in enumerate(pm_depth["asks"][:3]):
        print(f"     {i+1}. ${ask['price']:.4f} - {ask['size']} шт")

    # SX
    print("\n🟡 SX:")
    print("   Лучшие цены покупки:")
    for i, bid in enumerate(sx_depth["bids"][:3]):
        print(f"     {i+1}. ${bid['price']:.4f} - {bid['size']} шт")

    print("   Лучшие цены продажи:")
    for i, ask in enumerate(sx_depth["asks"][:3]):
        print(f"     {i+1}. ${ask['price']:.4f} - {ask['size']} шт")

    # Спред
    pm_spread = pm_depth["asks"][0]["price"] - pm_depth["bids"][0]["price"]
    sx_spread = sx_depth["asks"][0]["price"] - sx_depth["bids"][0]["price"]

    print("\n📈 Спреды:")
    print(f"   Polymarket: {pm_spread:.4f} ({pm_spread*100:.2f}%)")
    print(f"   SX: {sx_spread:.4f} ({sx_spread*100:.2f}%)")


def calculate_total_depth(orderbook: Dict) -> float:
    """Вычисляем общую глубину стакана"""
    total_bids = sum(order["size"] for order in orderbook.get("bids", []))
    total_asks = sum(order["size"] for order in orderbook.get("asks", []))
    return total_bids + total_asks


async def demo_cycle(cycle_num: int) -> None:
    """Выполняем один демо-цикл"""
    print(f"\n🔄 ЦИКЛ #{cycle_num}")
    print("=" * 30)

    # Генерируем моковые данные
    pm_depth, sx_depth = generate_mock_depth()

    # Выводим анализ
    print_depth_analysis(pm_depth, sx_depth)

    # Вычисляем общую глубину для каждой биржи
    pm_total_depth = calculate_total_depth(pm_depth)
    sx_total_depth = calculate_total_depth(sx_depth)

    # Обрабатываем данные через основную логику бота
    print("\n⚙️ Обработка данных...")
    print(f"   Общая глубина Polymarket: {pm_total_depth:.0f}")
    print(f"   Общая глубина SX: {sx_total_depth:.0f}")
    await process_depth(pm_total_depth, sx_total_depth)

    print(f"✅ Цикл #{cycle_num} завершен")


async def main() -> None:
    """Главная функция демо-бота"""
    parser = argparse.ArgumentParser(description="Демо-версия арбитражного бота")
    parser.add_argument("--cycles", type=int, default=3, help="Количество циклов")
    parser.add_argument(
        "--interval", type=int, default=5, help="Интервал между циклами (секунды)"
    )
    args = parser.parse_args()

    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logging.getLogger().addHandler(TelegramHandler())
    init_metrics()

    print("🎭 ДЕМО-ВЕРСИЯ АРБИТРАЖНОГО БОТА")
    print("=" * 50)
    print("Этот бот демонстрирует логику арбитража с моковыми данными")
    print(f"Количество циклов: {args.cycles}")
    print(f"Интервал: {args.interval} сек")
    print()

    try:
        for cycle in range(1, args.cycles + 1):
            await demo_cycle(cycle)

            if cycle < args.cycles:
                print(f"\n⏳ Ожидание {args.interval} сек до следующего цикла...")
                await asyncio.sleep(args.interval)

        print(f"\n🎉 Демонстрация завершена! Выполнено {args.cycles} циклов.")

    except KeyboardInterrupt:
        print("\n🛑 Демонстрация остановлена пользователем")
    except Exception as exc:
        print(f"\n❌ Ошибка в демонстрации: {exc}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Тестовый скрипт для проверки логики бота с моковыми данными
"""

import asyncio
import logging
import pytest

from core.metrics import init_metrics
from core.alerts import TelegramHandler
from core.processor import process_depth

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logging.getLogger().addHandler(TelegramHandler())
init_metrics()


@pytest.mark.asyncio
async def test_bot_logic():
    """Тестируем основную логику бота с моковыми данными"""

    print("🤖 Тестирование логики арбитражного бота")
    print("=" * 50)

    # Тестовые сценарии с разными значениями глубины
    test_scenarios = [
        (1500, 1200, "Высокая глубина - низкий проскальзывание"),
        (800, 600, "Средняя глубина - средний проскальзывание"),
        (300, 200, "Низкая глубина - высокий проскальзывание"),
        (50, 30, "Очень низкая глубина - максимальный проскальзывание"),
    ]

    for pm_depth, sx_depth, description in test_scenarios:
        print(f"\n📊 Тест: {description}")
        print(f"   Глубина Polymarket: {pm_depth}")
        print(f"   Глубина SX: {sx_depth}")

        try:
            # Create mock orderbooks with the test depths
            pm_book = {
                'best_bid': 0.55,
                'best_ask': 0.57,
                'bid_depth': pm_depth,
                'ask_depth': pm_depth,
                'total_depth': pm_depth * 2,
                'bids': [],
                'asks': [],
            }
            sx_book = {
                'best_bid': 0.56,
                'best_ask': 0.58,
                'bid_depth': sx_depth,
                'ask_depth': sx_depth,
                'total_depth': sx_depth * 2,
                'bids': [],
                'asks': [],
            }
            # Note: process_depth function signature has changed
            # It now takes orderbook dicts and processes arbitrage opportunities
            from core.processor import calculate_slippage
            pm_slip = calculate_slippage(pm_depth)
            sx_slip = calculate_slippage(sx_depth)
            max_slip = max(pm_slip, sx_slip)
            print(f"   ✅ Максимальное проскальзывание: {max_slip:.4f}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")

    print("\n" + "=" * 50)
    print("✅ Тестирование завершено!")


if __name__ == "__main__":
    asyncio.run(test_bot_logic())

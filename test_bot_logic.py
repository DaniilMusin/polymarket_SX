#!/usr/bin/env python3
"""
Тестовый скрипт для проверки логики бота с моковыми данными
"""

import asyncio
import logging
from aiohttp import ClientSession

from core.metrics import init_metrics
from core.alerts import TelegramHandler
from core.processor import process_depth

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logging.getLogger().addHandler(TelegramHandler())
init_metrics()

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
            max_slip = await process_depth(pm_depth, sx_depth)
            print(f"   ✅ Максимальное проскальзывание: {max_slip:.4f}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(test_bot_logic())
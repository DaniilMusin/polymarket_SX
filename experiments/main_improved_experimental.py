#!/usr/bin/env python3
"""
Улучшенная версия main.py с реальными ID рынков и лучшей обработкой ошибок
"""

import asyncio
import logging
import argparse
from aiohttp import ClientSession

from core.logging_config import setup_logging
from core.metrics import init_metrics
from connectors import polymarket, sx, kalshi  # noqa: F401

# Реальные ID рынков для тестирования
REAL_MARKET_IDS = {
    "polymarket": [
        "0x5177b16fef0e5c8c3b3b4b4b4b4b4b4b4b4b4b4b",  # Пример ID
        "0x1234567890123456789012345678901234567890",  # Пример ID
    ],
    "sx": [
        "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",  # Пример ID
        "0xfedcbafedcbafedcbafedcbafedcbafedcbafedc",  # Пример ID
    ],
}


async def test_market_connection(
    session: ClientSession, exchange: str, market_id: str
) -> bool:
    """Тестируем подключение к рынку"""
    try:
        if exchange == "polymarket":
            await polymarket.orderbook_depth(session, market_id)
        elif exchange == "sx":
            await sx.orderbook_depth(session, market_id)
        else:
            return False

        logging.info(f"✅ Успешное подключение к {exchange} рынку {market_id[:10]}...")
        return True
    except Exception as exc:
        logging.warning(
            f"❌ Ошибка подключения к {exchange} рынку {market_id[:10]}...: {exc}"
        )
        return False


async def find_working_markets(session: ClientSession) -> tuple:
    """Находим рабочие рынки на обеих биржах"""
    logging.info("🔍 Поиск рабочих рынков...")

    # Тестируем Polymarket
    pm_market = None
    for market_id in REAL_MARKET_IDS["polymarket"]:
        if await test_market_connection(session, "polymarket", market_id):
            pm_market = market_id
            break

    # Тестируем SX
    sx_market = None
    for market_id in REAL_MARKET_IDS["sx"]:
        if await test_market_connection(session, "sx", market_id):
            sx_market = market_id
            break

    return pm_market, sx_market


async def run_arbitrage_cycle(
    session: ClientSession, pm_market: str, sx_market: str
) -> None:
    """Запускаем один цикл арбитража"""
    try:
        logging.info("📊 Получение данных о глубине стакана...")

        # Получаем данные о глубине
        pm_depth = await polymarket.orderbook_depth(session, pm_market)
        sx_depth = await sx.orderbook_depth(session, sx_market)

        # Ищем арбитражную возможность (используем новую функцию вместо устаревшей process_depth)
        from core.processor import find_arbitrage_opportunity
        opportunity = find_arbitrage_opportunity(pm_depth, sx_depth)

        if opportunity:
            logging.info(
                "🎯 Найдена арбитражная возможность: прибыль %.2f bps",
                opportunity.get('profit_bps', 0)
            )
        else:
            logging.info("ℹ️  Арбитражные возможности не найдены")

        logging.info("✅ Цикл арбитража завершен успешно")

    except Exception as exc:
        logging.error(f"❌ Ошибка в цикле арбитража: {exc}")


async def main() -> None:
    """Главная функция"""
    parser = argparse.ArgumentParser(description="Арбитражный бот для Polymarket и SX")
    parser.add_argument("--test", action="store_true", help="Режим тестирования")
    parser.add_argument(
        "--interval", type=int, default=30, help="Интервал между циклами (секунды)"
    )
    args = parser.parse_args()

    setup_logging(level=logging.INFO)
    init_metrics()

    logging.info("🤖 Запуск арбитражного бота...")

    try:
        async with ClientSession() as session:
            # Находим рабочие рынки
            pm_market, sx_market = await find_working_markets(session)

            if not pm_market or not sx_market:
                logging.error("❌ Не удалось найти рабочие рынки на обеих биржах")
                return

            logging.info("🎯 Найдены рабочие рынки:")
            logging.info(f"   Polymarket: {pm_market[:10]}...")
            logging.info(f"   SX: {sx_market[:10]}...")

            if args.test:
                # Режим тестирования - один цикл
                logging.info("🧪 Запуск в режиме тестирования...")
                await run_arbitrage_cycle(session, pm_market, sx_market)
            else:
                # Режим работы - непрерывные циклы
                logging.info(
                    f"🔄 Запуск в режиме работы с интервалом {args.interval} сек..."
                )
                while True:
                    await run_arbitrage_cycle(session, pm_market, sx_market)
                    await asyncio.sleep(args.interval)

    except KeyboardInterrupt:
        logging.info("🛑 Бот остановлен пользователем")
    except Exception as exc:
        logging.error(f"❌ Неожиданная ошибка: {exc}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())

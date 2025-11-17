"""Tests for input validation in execute_arbitrage_trade."""

import pytest
import asyncio
from unittest.mock import MagicMock


def test_execute_arbitrage_trade_validates_opportunity_dict():
    """Test that execute_arbitrage_trade validates opportunity dictionary."""
    from core.trader import execute_arbitrage_trade

    async def run_test():
        session = MagicMock()

        # Test None opportunity
        with pytest.raises(ValueError, match="Invalid opportunity: must be a non-empty dictionary"):
            await execute_arbitrage_trade(
                session=session,
                opportunity=None,
                pm_market_id='test',
                sx_market_id='test'
            )

        # Test empty dict
        with pytest.raises(ValueError, match="Invalid opportunity: must be a non-empty dictionary"):
            await execute_arbitrage_trade(
                session=session,
                opportunity={},
                pm_market_id='test',
                sx_market_id='test'
            )

        # Test missing required keys
        with pytest.raises(ValueError, match="missing required keys"):
            await execute_arbitrage_trade(
                session=session,
                opportunity={'buy_exchange': 'polymarket'},
                pm_market_id='test',
                sx_market_id='test'
            )

    asyncio.run(run_test())


def test_execute_arbitrage_trade_validates_exchange_names():
    """Test that exchange names are validated."""
    from core.trader import execute_arbitrage_trade

    async def run_test():
        session = MagicMock()

        # Test same exchange
        with pytest.raises(ValueError, match="buy and sell exchanges must be different"):
            await execute_arbitrage_trade(
                session=session,
                opportunity={
                    'buy_exchange': 'polymarket',
                    'sell_exchange': 'polymarket',
                    'buy_price': 0.4,
                    'sell_price': 0.6,
                    'position_size': 10.0
                },
                pm_market_id='test',
                sx_market_id='test'
            )

        # Test invalid exchange name
        with pytest.raises(ValueError, match="Invalid buy_exchange"):
            await execute_arbitrage_trade(
                session=session,
                opportunity={
                    'buy_exchange': 'invalid_exchange',
                    'sell_exchange': 'sx',
                    'buy_price': 0.4,
                    'sell_price': 0.6,
                    'position_size': 10.0
                },
                pm_market_id='test',
                sx_market_id='test'
            )

    asyncio.run(run_test())


def test_execute_arbitrage_trade_validates_types():
    """Test that types are validated."""
    from core.trader import execute_arbitrage_trade

    async def run_test():
        session = MagicMock()

        # Test non-string exchange
        with pytest.raises(ValueError, match="Exchange names must be strings"):
            await execute_arbitrage_trade(
                session=session,
                opportunity={
                    'buy_exchange': 123,  # Invalid type
                    'sell_exchange': 'sx',
                    'buy_price': 0.4,
                    'sell_price': 0.6,
                    'position_size': 10.0
                },
                pm_market_id='test',
                sx_market_id='test'
            )

        # Test non-numeric price
        with pytest.raises(ValueError, match="Prices must be numeric"):
            await execute_arbitrage_trade(
                session=session,
                opportunity={
                    'buy_exchange': 'polymarket',
                    'sell_exchange': 'sx',
                    'buy_price': 'invalid',  # Invalid type
                    'sell_price': 0.6,
                    'position_size': 10.0
                },
                pm_market_id='test',
                sx_market_id='test'
            )

        # Test non-numeric size
        with pytest.raises(ValueError, match="Size must be numeric"):
            await execute_arbitrage_trade(
                session=session,
                opportunity={
                    'buy_exchange': 'polymarket',
                    'sell_exchange': 'sx',
                    'buy_price': 0.4,
                    'sell_price': 0.6,
                    'position_size': 'invalid'  # Invalid type
                },
                pm_market_id='test',
                sx_market_id='test'
            )

    asyncio.run(run_test())


def test_execute_arbitrage_trade_validates_values():
    """Test that values are validated."""
    from core.trader import execute_arbitrage_trade

    async def run_test():
        session = MagicMock()

        # Test negative size
        with pytest.raises(ValueError, match="Size must be positive"):
            await execute_arbitrage_trade(
                session=session,
                opportunity={
                    'buy_exchange': 'polymarket',
                    'sell_exchange': 'sx',
                    'buy_price': 0.4,
                    'sell_price': 0.6,
                    'position_size': -10.0
                },
                pm_market_id='test',
                sx_market_id='test'
            )

        # Test zero size
        with pytest.raises(ValueError, match="Size must be positive"):
            await execute_arbitrage_trade(
                session=session,
                opportunity={
                    'buy_exchange': 'polymarket',
                    'sell_exchange': 'sx',
                    'buy_price': 0.4,
                    'sell_price': 0.6,
                    'position_size': 0.0
                },
                pm_market_id='test',
                sx_market_id='test'
            )

        # Test negative price
        with pytest.raises(ValueError, match="Prices must be positive"):
            await execute_arbitrage_trade(
                session=session,
                opportunity={
                    'buy_exchange': 'polymarket',
                    'sell_exchange': 'sx',
                    'buy_price': -0.4,
                    'sell_price': 0.6,
                    'position_size': 10.0
                },
                pm_market_id='test',
                sx_market_id='test'
            )

        # Test buy_price >= sell_price (would result in loss)
        with pytest.raises(ValueError, match="This would result in a loss"):
            await execute_arbitrage_trade(
                session=session,
                opportunity={
                    'buy_exchange': 'polymarket',
                    'sell_exchange': 'sx',
                    'buy_price': 0.6,
                    'sell_price': 0.4,  # Lower than buy!
                    'position_size': 10.0
                },
                pm_market_id='test',
                sx_market_id='test'
            )

    asyncio.run(run_test())


def test_case_insensitive_exchange_names():
    """Test that exchange name validation is case-insensitive."""
    from core.trader import execute_arbitrage_trade

    async def run_test():
        session = MagicMock()
        wallet = MagicMock()

        # Should accept POLYMARKET (uppercase)
        # Will fail at execution (no API calls), but validation should pass
        try:
            await execute_arbitrage_trade(
                session=session,
                opportunity={
                    'buy_exchange': 'POLYMARKET',  # Uppercase
                    'sell_exchange': 'SX',  # Uppercase
                    'buy_price': 0.4,
                    'sell_price': 0.6,
                    'position_size': 10.0
                },
                pm_market_id='test',
                sx_market_id='test',
                wallet=wallet,
                dry_run=True  # Dry run to avoid API calls
            )
        except Exception as e:
            # Should not get ValueError for exchange names
            assert not isinstance(e, ValueError) or 'Invalid' not in str(e)

    asyncio.run(run_test())

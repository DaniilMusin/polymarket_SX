"""
End-to-End Integration Tests for Arbitrage Pipeline

These tests simulate the complete arbitrage flow:
1. Finding opportunities
2. Reserving risk and balance
3. Executing orders
4. Handling successes and failures
5. Cleaning up resources

All tests use mocked exchange APIs to avoid real orders.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientSession

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.processor import find_arbitrage_opportunity
from core.trader import execute_arbitrage_trade, TradeExecutionError
from core.risk import get_risk_manager, PanicError
from core.exchange_balances import get_balance_manager, reset_balance_manager
from core.wallet import Wallet
from core.statistics import get_statistics_collector
from core.metrics import g_trades, g_edge, update_pnl


@pytest.fixture(autouse=True)
def reset_managers():
    """Reset all managers before each test."""
    reset_balance_manager()
    # Reset risk manager
    risk_mgr = get_risk_manager()
    risk_mgr._exchange_exposure = {"polymarket": 0.0, "sx": 0.0, "kalshi": 0.0}
    risk_mgr._market_exposure = {}
    risk_mgr._open_arbs = 0
    risk_mgr._panic_reason = None
    yield


@pytest.fixture
def mock_wallet():
    """Create a mock wallet."""
    with patch('core.wallet.Wallet') as MockWallet:
        wallet = MockWallet.return_value
        wallet.address = "0x1234567890123456789012345678901234567890"
        wallet.sign_message = MagicMock(return_value="0xmockedsignature")
        yield wallet


@pytest.fixture
def good_orderbooks():
    """Orderbooks with clear arbitrage opportunity."""
    pm_book = {
        'best_bid': 0.45,
        'best_ask': 0.47,
        'bid_depth': 450.0,
        'ask_depth': 470.0,
        'total_depth': 920.0,
        'bid_qty_depth': 1000.0,
        'ask_qty_depth': 1000.0,
        'total_qty_depth': 2000.0,
        'bid_notional_depth': 450.0,
        'ask_notional_depth': 470.0,
        'total_notional_depth': 920.0,
        'bids': [{'price': 0.45, 'size': 1000.0}],
        'asks': [{'price': 0.47, 'size': 1000.0}],
    }

    sx_book = {
        'best_bid': 0.53,  # Higher bid - we can sell here
        'best_ask': 0.55,
        'bid_depth': 530.0,
        'ask_depth': 550.0,
        'total_depth': 1080.0,
        'bid_qty_depth': 1000.0,
        'ask_qty_depth': 1000.0,
        'total_qty_depth': 2000.0,
        'bid_notional_depth': 530.0,
        'ask_notional_depth': 550.0,
        'total_notional_depth': 1080.0,
        'bids': [{'price': 0.53, 'size': 1000.0}],
        'asks': [{'price': 0.55, 'size': 1000.0}],
    }

    return pm_book, sx_book


@pytest.mark.asyncio
async def test_e2e_successful_arbitrage(mock_wallet, good_orderbooks):
    """
    Test complete successful arbitrage flow:
    - Find opportunity
    - Reserve risk/balance
    - Execute both legs
    - Commit resources
    - Update metrics
    """
    pm_book, sx_book = good_orderbooks

    # Find opportunity
    opportunity = find_arbitrage_opportunity(
        pm_book, sx_book,
        pm_market_id="pm-test-market",
        sx_market_id="sx-test-market",
        pm_outcome="yes",
        sx_outcome="yes",
    )

    assert opportunity is not None
    assert opportunity['buy_exchange'] == 'polymarket'
    assert opportunity['sell_exchange'] == 'sx'
    assert opportunity['profit_bps'] > 0

    # Mock successful order responses (both filled)
    successful_pm_response = {
        'status': 'FILLED',
        'orderID': 'pm-order-123',
        'size_matched': opportunity['buy_notional'],
    }

    successful_sx_response = {
        'state': 'FILLED',
        'orderId': 'sx-order-456',
        'filled_size': opportunity['sell_notional'],
    }

    # Mock the order placement functions
    with patch('core.trader.place_order_polymarket', new_callable=AsyncMock) as mock_pm_order, \
         patch('core.trader.place_order_sx', new_callable=AsyncMock) as mock_sx_order:

        mock_pm_order.return_value = {
            'status': 'success',
            'exchange': 'polymarket',
            'order_id': 'pm-order-123',
            'response': successful_pm_response,
        }

        mock_sx_order.return_value = {
            'status': 'success',
            'exchange': 'sx',
            'order_id': 'sx-order-456',
            'response': successful_sx_response,
        }

        # Execute trade (dry_run=False to test real flow, but orders are mocked)
        async with ClientSession() as session:
            result = await execute_arbitrage_trade(
                session,
                opportunity,
                pm_market_id="pm-test-market",
                sx_market_id="sx-test-market",
                pm_token_id="test-token-id",
                wallet=mock_wallet,
                dry_run=False
            )

    # Verify results
    assert result['status'] == 'executed'
    assert result['buy_exchange'] == 'polymarket'
    assert result['sell_exchange'] == 'sx'
    assert 'buy_order' in result
    assert 'sell_order' in result

    # Verify both orders were placed
    assert mock_pm_order.called
    assert mock_sx_order.called

    # Verify balance manager state
    balance_mgr = get_balance_manager()
    # After successful trade, balances should be committed (decreased)
    pm_balance = balance_mgr.get_balance('polymarket')
    sx_balance = balance_mgr.get_balance('sx')

    # Initial balance is $10, notional per leg should be small
    assert pm_balance < 10.0
    assert sx_balance < 10.0

    # No locked balance should remain
    assert balance_mgr.get_locked_balance('polymarket') == 0.0
    assert balance_mgr.get_locked_balance('sx') == 0.0

    # Verify risk manager state
    risk_mgr = get_risk_manager()
    # After trade completion, risk should be released
    assert risk_mgr._open_arbs == 0
    assert not risk_mgr.is_panic()


@pytest.mark.asyncio
async def test_e2e_partial_fill_scenario(mock_wallet, good_orderbooks):
    """
    Test partial fill scenario:
    - Buy order fills
    - Sell order returns partial fill status
    - Should trigger unhedged leg handling
    - Should enter panic mode
    """
    pm_book, sx_book = good_orderbooks

    # Find opportunity
    opportunity = find_arbitrage_opportunity(
        pm_book, sx_book,
        pm_market_id="pm-test-market",
        sx_market_id="sx-test-market",
        pm_outcome="yes",
        sx_outcome="yes",
    )

    assert opportunity is not None

    # Mock buy order success, sell order partial fill
    successful_pm_response = {
        'status': 'FILLED',
        'orderID': 'pm-order-123',
        'size_matched': opportunity['buy_notional'],
    }

    # Sell order returns CANCELLED (IOC didn't fully fill)
    failed_sx_response = {
        'state': 'CANCELLED',
        'orderId': 'sx-order-456',
        'filled_size': 0.0,  # Not filled
    }

    # Mock the order placement functions
    with patch('core.trader.place_order_polymarket', new_callable=AsyncMock) as mock_pm_order, \
         patch('core.trader.place_order_sx', new_callable=AsyncMock) as mock_sx_order, \
         patch('core.trader.send_critical_alert', new_callable=AsyncMock) as mock_alert:

        mock_pm_order.return_value = {
            'status': 'success',
            'exchange': 'polymarket',
            'order_id': 'pm-order-123',
            'response': successful_pm_response,
        }

        # Sell order will raise TradeExecutionError due to CANCELLED status
        # This simulates check_ioc_order_filled detecting the issue
        mock_sx_order.return_value = {
            'status': 'success',
            'exchange': 'sx',
            'order_id': 'sx-order-456',
            'response': failed_sx_response,
        }

        # Execute trade - should fail with TradeExecutionError
        with pytest.raises(TradeExecutionError) as exc_info:
            async with ClientSession() as session:
                await execute_arbitrage_trade(
                    session,
                    opportunity,
                    pm_market_id="pm-test-market",
                    sx_market_id="sx-test-market",
                    pm_token_id="test-token-id",
                    wallet=mock_wallet,
                    dry_run=False
                )

        # Verify error message mentions unhedged position
        assert "Sell leg failed while buy leg filled" in str(exc_info.value) or \
               "Arbitrage failed" in str(exc_info.value)

    # Verify panic mode was triggered
    risk_mgr = get_risk_manager()
    assert risk_mgr.is_panic()

    # Verify balances were properly cleaned up
    balance_mgr = get_balance_manager()
    # Buy order executed, so balance should be committed
    # Sell order failed, so its balance should be released
    assert balance_mgr.get_locked_balance('polymarket') == 0.0
    assert balance_mgr.get_locked_balance('sx') == 0.0


@pytest.mark.asyncio
async def test_e2e_both_orders_fail(mock_wallet, good_orderbooks):
    """
    Test scenario where both orders fail:
    - Should raise TradeExecutionError
    - Should NOT enter panic mode (no unhedged position)
    - Should release all reserved balances
    """
    pm_book, sx_book = good_orderbooks

    opportunity = find_arbitrage_opportunity(
        pm_book, sx_book,
        pm_market_id="pm-test-market",
        sx_market_id="sx-test-market",
        pm_outcome="yes",
        sx_outcome="yes",
    )

    # Both orders fail
    with patch('core.trader.place_order_polymarket', new_callable=AsyncMock) as mock_pm_order, \
         patch('core.trader.place_order_sx', new_callable=AsyncMock) as mock_sx_order:

        # Both return errors
        mock_pm_order.side_effect = TradeExecutionError("PM API error")
        mock_sx_order.side_effect = TradeExecutionError("SX API error")

        with pytest.raises(TradeExecutionError):
            async with ClientSession() as session:
                await execute_arbitrage_trade(
                    session,
                    opportunity,
                    pm_market_id="pm-test-market",
                    sx_market_id="sx-test-market",
                    pm_token_id="test-token-id",
                    wallet=mock_wallet,
                    dry_run=False
                )

    # Verify NO panic mode (both failed, no unhedged position)
    risk_mgr = get_risk_manager()
    assert not risk_mgr.is_panic()

    # Verify all balances released
    balance_mgr = get_balance_manager()
    assert balance_mgr.get_locked_balance('polymarket') == 0.0
    assert balance_mgr.get_locked_balance('sx') == 0.0

    # Verify original balances restored
    assert balance_mgr.get_balance('polymarket') == 10.0
    assert balance_mgr.get_balance('sx') == 10.0


@pytest.mark.asyncio
async def test_e2e_insufficient_balance(good_orderbooks):
    """
    Test scenario where balance is insufficient:
    - Should raise InsufficientBalanceError before placing orders
    - Should NOT reserve any risk
    - Should NOT place any orders
    """
    pm_book, sx_book = good_orderbooks

    # Create opportunity with large position size
    opportunity = find_arbitrage_opportunity(
        pm_book, sx_book,
        pm_market_id="pm-test-market",
        sx_market_id="sx-test-market",
        pm_outcome="yes",
        sx_outcome="yes",
    )

    # Force very large position size
    opportunity['position_size'] = 1000.0  # Much larger than $10 balance
    opportunity['qty'] = 1000.0

    balance_manager = get_balance_manager()
    with balance_manager._lock:
        balance_manager._balances["polymarket"] = 1.0
        balance_manager._balances["sx"] = 1.0
    initial_pm_balance = balance_manager.get_balance("polymarket")
    initial_sx_balance = balance_manager.get_balance("sx")

    with patch('core.trader.place_order_polymarket', new_callable=AsyncMock) as mock_pm_order, \
         patch('core.trader.place_order_sx', new_callable=AsyncMock) as mock_sx_order:

        with pytest.raises(TradeExecutionError) as exc_info:
            async with ClientSession() as session:
                # Need a mock wallet
                mock_wallet = MagicMock()
                mock_wallet.address = "0xtest"

                await execute_arbitrage_trade(
                    session,
                    opportunity,
                    pm_market_id="pm-test-market",
                    sx_market_id="sx-test-market",
                    pm_token_id="test-token-id",
                    wallet=mock_wallet,
                    dry_run=False
                )

        # Error should mention insufficient balance or risk limits
        # Can be either from balance manager ("Insufficient balance")
        # or risk manager ("лимит экспозиции" / "exposure limit")
        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in [
            "insufficient balance", "balance", "экспозиции", "exposure"
        ])

        # Verify NO orders were placed
        assert not mock_pm_order.called
        assert not mock_sx_order.called

    # Verify no panic mode
    risk_mgr = get_risk_manager()
    assert not risk_mgr.is_panic()

    # Verify balances unchanged
    balance_mgr = get_balance_manager()
    assert balance_mgr.get_balance('polymarket') == initial_pm_balance
    assert balance_mgr.get_balance('sx') == initial_sx_balance
    assert balance_mgr.get_locked_balance('polymarket') == 0.0
    assert balance_mgr.get_locked_balance('sx') == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

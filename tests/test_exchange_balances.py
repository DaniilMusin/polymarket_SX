"""Tests for exchange balance management."""

import os
import pytest
from core.exchange_balances import (
    ExchangeBalanceManager,
    InsufficientBalanceError,
    get_balance_manager,
    reset_balance_manager,
)


@pytest.fixture
def balance_manager():
    """Create a fresh balance manager for testing."""
    # Clear environment variables
    for key in ['EXCHANGE_INITIAL_BALANCE', 'POLYMARKET_BALANCE', 'SX_BALANCE', 'KALSHI_BALANCE']:
        if key in os.environ:
            del os.environ[key]

    # Reset global instance
    reset_balance_manager()

    # Set test balances
    os.environ['EXCHANGE_INITIAL_BALANCE'] = '10.0'

    manager = ExchangeBalanceManager()
    return manager


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up after each test."""
    yield
    # Reset global instance after each test
    reset_balance_manager()


def test_initial_balances(balance_manager):
    """Test that initial balances are set correctly."""
    assert balance_manager.get_balance('polymarket') == 10.0
    assert balance_manager.get_balance('sx') == 10.0
    assert balance_manager.get_balance('kalshi') == 10.0


def test_custom_balances():
    """Test setting custom balances for each exchange."""
    os.environ['POLYMARKET_BALANCE'] = '20.0'
    os.environ['SX_BALANCE'] = '30.0'
    os.environ['KALSHI_BALANCE'] = '40.0'

    manager = ExchangeBalanceManager()

    assert manager.get_balance('polymarket') == 20.0
    assert manager.get_balance('sx') == 30.0
    assert manager.get_balance('kalshi') == 40.0


def test_check_balance(balance_manager):
    """Test balance checking."""
    assert balance_manager.check_balance('polymarket', 5.0) is True
    assert balance_manager.check_balance('polymarket', 10.0) is True
    assert balance_manager.check_balance('polymarket', 15.0) is False


def test_reserve_balance(balance_manager):
    """Test reserving balance."""
    initial_available = balance_manager.get_balance('polymarket')
    initial_locked = balance_manager.get_locked_balance('polymarket')

    balance_manager.reserve_balance('polymarket', 5.0)

    assert balance_manager.get_balance('polymarket') == initial_available - 5.0
    assert balance_manager.get_locked_balance('polymarket') == initial_locked + 5.0


def test_reserve_insufficient_balance(balance_manager):
    """Test that reserving more than available raises error."""
    with pytest.raises(InsufficientBalanceError):
        balance_manager.reserve_balance('polymarket', 15.0)


def test_commit_order(balance_manager):
    """Test committing an order."""
    balance_manager.reserve_balance('polymarket', 5.0)
    initial_locked = balance_manager.get_locked_balance('polymarket')

    balance_manager.commit_order('polymarket', 5.0)

    assert balance_manager.get_locked_balance('polymarket') == initial_locked - 5.0


def test_release_balance(balance_manager):
    """Test releasing reserved balance."""
    balance_manager.reserve_balance('polymarket', 5.0)
    initial_available = balance_manager.get_balance('polymarket')

    balance_manager.release_balance('polymarket', 5.0)

    assert balance_manager.get_balance('polymarket') == initial_available + 5.0
    assert balance_manager.get_locked_balance('polymarket') == 0.0


def test_full_trade_cycle(balance_manager):
    """Test a full trade cycle: reserve -> commit."""
    initial_total = balance_manager.get_total_balance('polymarket')

    # Reserve balance for order
    balance_manager.reserve_balance('polymarket', 5.0)
    assert balance_manager.get_balance('polymarket') == 5.0
    assert balance_manager.get_locked_balance('polymarket') == 5.0

    # Commit order (order was successful)
    balance_manager.commit_order('polymarket', 5.0)
    assert balance_manager.get_balance('polymarket') == 5.0
    assert balance_manager.get_locked_balance('polymarket') == 0.0

    # Total balance should have decreased
    assert balance_manager.get_total_balance('polymarket') == initial_total - 5.0


def test_failed_trade_cycle(balance_manager):
    """Test a failed trade cycle: reserve -> release."""
    initial_total = balance_manager.get_total_balance('polymarket')

    # Reserve balance for order
    balance_manager.reserve_balance('polymarket', 5.0)
    assert balance_manager.get_balance('polymarket') == 5.0
    assert balance_manager.get_locked_balance('polymarket') == 5.0

    # Release balance (order failed)
    balance_manager.release_balance('polymarket', 5.0)
    assert balance_manager.get_balance('polymarket') == 10.0
    assert balance_manager.get_locked_balance('polymarket') == 0.0

    # Total balance should be unchanged
    assert balance_manager.get_total_balance('polymarket') == initial_total


def test_multiple_orders(balance_manager):
    """Test handling multiple simultaneous orders."""
    # Reserve for first order
    balance_manager.reserve_balance('polymarket', 3.0)
    assert balance_manager.get_balance('polymarket') == 7.0

    # Reserve for second order
    balance_manager.reserve_balance('polymarket', 4.0)
    assert balance_manager.get_balance('polymarket') == 3.0
    assert balance_manager.get_locked_balance('polymarket') == 7.0

    # Cannot reserve more (only 3.0 available)
    with pytest.raises(InsufficientBalanceError):
        balance_manager.reserve_balance('polymarket', 4.0)

    # Commit first order
    balance_manager.commit_order('polymarket', 3.0)
    assert balance_manager.get_locked_balance('polymarket') == 4.0

    # Release second order
    balance_manager.release_balance('polymarket', 4.0)
    assert balance_manager.get_balance('polymarket') == 7.0
    assert balance_manager.get_locked_balance('polymarket') == 0.0


def test_reset_balances(balance_manager):
    """Test resetting balances."""
    balance_manager.reserve_balance('polymarket', 5.0)
    balance_manager.commit_order('polymarket', 5.0)

    assert balance_manager.get_balance('polymarket') == 5.0

    balance_manager.reset_balances()

    assert balance_manager.get_balance('polymarket') == 10.0
    assert balance_manager.get_locked_balance('polymarket') == 0.0


def test_get_all_balances(balance_manager):
    """Test getting all balances."""
    balance_manager.reserve_balance('polymarket', 3.0)

    all_balances = balance_manager.get_all_balances()

    assert all_balances['polymarket']['available'] == 7.0
    assert all_balances['polymarket']['locked'] == 3.0
    assert all_balances['polymarket']['total'] == 10.0
    assert all_balances['polymarket']['initial'] == 10.0

    assert all_balances['sx']['available'] == 10.0
    assert all_balances['kalshi']['available'] == 10.0


def test_global_balance_manager():
    """Test global balance manager singleton."""
    reset_balance_manager()

    manager1 = get_balance_manager()
    manager2 = get_balance_manager()

    assert manager1 is manager2

    manager1.reserve_balance('polymarket', 5.0)
    assert manager2.get_locked_balance('polymarket') == 5.0


def test_case_insensitive_exchange_names(balance_manager):
    """Test that exchange names are case-insensitive."""
    balance_manager.reserve_balance('POLYMARKET', 5.0)
    assert balance_manager.get_balance('polymarket') == 5.0

    balance_manager.reserve_balance('Sx', 3.0)
    assert balance_manager.get_balance('sx') == 7.0


def test_commit_more_than_locked(balance_manager):
    """Test committing more than locked amount (edge case)."""
    balance_manager.reserve_balance('polymarket', 5.0)

    # This should log a warning but not crash
    balance_manager.commit_order('polymarket', 10.0)

    assert balance_manager.get_locked_balance('polymarket') == 0.0


def test_release_more_than_locked(balance_manager):
    """Test releasing more than locked amount (edge case)."""
    balance_manager.reserve_balance('polymarket', 5.0)
    initial_available = balance_manager.get_balance('polymarket')

    # This should only release what's locked
    balance_manager.release_balance('polymarket', 10.0)

    # Should have released 5.0 (what was locked)
    assert balance_manager.get_balance('polymarket') == initial_available + 5.0
    assert balance_manager.get_locked_balance('polymarket') == 0.0


def test_thread_safety():
    """Basic test for thread safety (reserve/release from multiple operations)."""
    import threading

    reset_balance_manager()
    os.environ['EXCHANGE_INITIAL_BALANCE'] = '100.0'
    manager = ExchangeBalanceManager()

    errors = []

    def reserve_and_release():
        try:
            for _ in range(10):
                manager.reserve_balance('polymarket', 5.0)
                manager.release_balance('polymarket', 5.0)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=reserve_and_release) for _ in range(5)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # Should complete without errors
    assert len(errors) == 0
    assert manager.get_balance('polymarket') == 100.0
    assert manager.get_locked_balance('polymarket') == 0.0

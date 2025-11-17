"""
Exchange Balance Management Module

This module manages virtual balances for each exchange to control risk and limit exposure.
Even if real balances on exchanges are higher, only the configured virtual balance can be used.

Features:
- Set initial balance for each exchange (default: $10)
- Track available balance after orders
- Prevent orders that exceed available balance
- Reset balances when needed
"""

import os
import logging
from typing import Dict, Optional
from threading import Lock


class InsufficientBalanceError(Exception):
    """Raised when trying to place an order with insufficient balance."""


class ExchangeBalanceManager:
    """
    Manages virtual balances for exchanges to control risk.

    This prevents the bot from using more funds than configured,
    even if real exchange balances are higher.
    """

    def __init__(self):
        """Initialize balance manager with configured initial balances."""
        # Thread-safe balance tracking
        self._lock = Lock()

        # Get initial balances from environment (default: $10 per exchange)
        default_balance = float(os.getenv('EXCHANGE_INITIAL_BALANCE', '10.0'))

        self._initial_balances = {
            'polymarket': float(os.getenv('POLYMARKET_BALANCE', str(default_balance))),
            'sx': float(os.getenv('SX_BALANCE', str(default_balance))),
            'kalshi': float(os.getenv('KALSHI_BALANCE', str(default_balance))),
        }

        # Current available balances (will decrease as orders are placed)
        self._balances = self._initial_balances.copy()

        # Track locked/pending funds
        self._locked_balances = {
            'polymarket': 0.0,
            'sx': 0.0,
            'kalshi': 0.0,
        }

        logging.info("Exchange balances initialized:")
        for exchange, balance in self._balances.items():
            logging.info("  %s: $%.2f", exchange, balance)

    def get_balance(self, exchange: str) -> float:
        """
        Get current available balance for an exchange.

        Args:
            exchange: Exchange name ('polymarket', 'sx', 'kalshi')

        Returns:
            Available balance in USD
        """
        with self._lock:
            balance = self._balances.get(exchange.lower(), 0.0)
            logging.debug("Get balance for %s: $%.2f", exchange, balance)
            return balance

    def get_locked_balance(self, exchange: str) -> float:
        """
        Get locked/pending balance for an exchange.

        Args:
            exchange: Exchange name

        Returns:
            Locked balance in USD
        """
        with self._lock:
            return self._locked_balances.get(exchange.lower(), 0.0)

    def get_total_balance(self, exchange: str) -> float:
        """
        Get total balance (available + locked) for an exchange.

        Args:
            exchange: Exchange name

        Returns:
            Total balance in USD
        """
        with self._lock:
            available = self._balances.get(exchange.lower(), 0.0)
            locked = self._locked_balances.get(exchange.lower(), 0.0)
            return available + locked

    def check_balance(self, exchange: str, amount: float) -> bool:
        """
        Check if sufficient balance is available for an order.

        Args:
            exchange: Exchange name
            amount: Required amount in USD

        Returns:
            True if sufficient balance, False otherwise
        """
        with self._lock:
            available = self._balances.get(exchange.lower(), 0.0)
            sufficient = available >= amount
            logging.debug(
                "Check balance for %s: required=$%.2f, available=$%.2f, sufficient=%s",
                exchange, amount, available, sufficient
            )
            return sufficient

    def reserve_balance(self, exchange: str, amount: float) -> None:
        """
        Reserve balance for an order (move from available to locked).

        This should be called before placing an order to prevent
        double-spending if multiple orders are placed simultaneously.

        Args:
            exchange: Exchange name
            amount: Amount to reserve in USD

        Raises:
            InsufficientBalanceError: If insufficient balance
        """
        exchange_lower = exchange.lower()

        with self._lock:
            available = self._balances.get(exchange_lower, 0.0)

            if available < amount:
                raise InsufficientBalanceError(
                    f"Insufficient balance on {exchange}: "
                    f"required ${amount:.2f}, available ${available:.2f}"
                )

            # Move from available to locked
            self._balances[exchange_lower] -= amount
            self._locked_balances[exchange_lower] += amount

            logging.info(
                "Reserved $%.2f on %s (available: $%.2f -> $%.2f, locked: $%.2f)",
                amount, exchange,
                available, self._balances[exchange_lower],
                self._locked_balances[exchange_lower]
            )

    def commit_order(self, exchange: str, amount: float) -> None:
        """
        Commit a successful order (deduct from locked balance).

        This should be called after an order is successfully filled.
        The funds are now used and removed from locked balance.

        Args:
            exchange: Exchange name
            amount: Amount that was used in USD
        """
        exchange_lower = exchange.lower()

        with self._lock:
            locked = self._locked_balances.get(exchange_lower, 0.0)

            if locked < amount:
                logging.warning(
                    "Commit amount $%.2f exceeds locked balance $%.2f on %s",
                    amount, locked, exchange
                )
                # Still commit, but log the issue
                self._locked_balances[exchange_lower] = 0.0
            else:
                self._locked_balances[exchange_lower] -= amount

            logging.info(
                "Committed $%.2f on %s (locked: $%.2f -> $%.2f)",
                amount, exchange, locked, self._locked_balances[exchange_lower]
            )

    def release_balance(self, exchange: str, amount: float) -> None:
        """
        Release reserved balance (move from locked back to available).

        This should be called if an order fails or is cancelled.

        Args:
            exchange: Exchange name
            amount: Amount to release in USD
        """
        exchange_lower = exchange.lower()

        with self._lock:
            locked = self._locked_balances.get(exchange_lower, 0.0)

            if locked < amount:
                logging.warning(
                    "Release amount $%.2f exceeds locked balance $%.2f on %s",
                    amount, locked, exchange
                )
                # Release whatever is locked
                release_amount = locked
            else:
                release_amount = amount

            # Move from locked back to available
            self._locked_balances[exchange_lower] -= release_amount
            self._balances[exchange_lower] += release_amount

            logging.info(
                "Released $%.2f on %s (available: $%.2f, locked: $%.2f)",
                release_amount, exchange,
                self._balances[exchange_lower],
                self._locked_balances[exchange_lower]
            )

    def reset_balances(self) -> None:
        """Reset all balances to initial values."""
        with self._lock:
            self._balances = self._initial_balances.copy()
            self._locked_balances = {
                'polymarket': 0.0,
                'sx': 0.0,
                'kalshi': 0.0,
            }
            logging.info("Balances reset to initial values")

    def get_all_balances(self) -> Dict[str, Dict[str, float]]:
        """
        Get all balances for all exchanges.

        Returns:
            Dictionary with balance info for each exchange
        """
        with self._lock:
            return {
                exchange: {
                    'available': self._balances[exchange],
                    'locked': self._locked_balances[exchange],
                    'total': self._balances[exchange] + self._locked_balances[exchange],
                    'initial': self._initial_balances[exchange],
                }
                for exchange in ['polymarket', 'sx', 'kalshi']
            }


# Global balance manager instance
_balance_manager: Optional[ExchangeBalanceManager] = None


def get_balance_manager() -> ExchangeBalanceManager:
    """
    Get or create the global balance manager instance.

    Returns:
        ExchangeBalanceManager instance
    """
    global _balance_manager
    if _balance_manager is None:
        logging.info("Initializing global balance manager")
        _balance_manager = ExchangeBalanceManager()
    return _balance_manager


def reset_balance_manager() -> None:
    """Reset the global balance manager (useful for testing)."""
    global _balance_manager
    logging.info("Resetting global balance manager")
    _balance_manager = None

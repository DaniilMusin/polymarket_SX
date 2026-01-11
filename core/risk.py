"""Risk management utilities for limiting exposure and triggering panic mode."""

from __future__ import annotations

import logging
import uuid
from threading import Lock
from typing import Dict, Optional

from config import (
    MAX_EXCHANGE_EXPOSURE,
    MAX_MARKET_EXPOSURE,
    MAX_OPEN_ARBITRAGES,
    PANIC_TRIGGER_ON_PARTIAL,
)
from core.alert_manager import get_alert_manager


class PanicError(Exception):
    """Raised when panic mode is active and trading should halt."""


class RiskManager:
    def __init__(self) -> None:
        self._lock = Lock()
        self._exchange_exposure: Dict[str, float] = {
            "polymarket": 0.0,
            "sx": 0.0,
            "kalshi": 0.0,
        }
        self._market_exposure: Dict[str, float] = {}
        self._open_arbs = 0
        self._panic_reason: Optional[str] = None

    def _log_state(self) -> None:
        logging.debug(
            "Risk state | panic=%s | open_arbs=%s | exposure=%s | markets=%s",
            bool(self._panic_reason),
            self._open_arbs,
            self._exchange_exposure,
            self._market_exposure,
        )

    def is_panic(self) -> bool:
        with self._lock:
            return self._panic_reason is not None

    def trigger_panic(self, reason: str) -> None:
        with self._lock:
            if self._panic_reason:
                return
            self._panic_reason = reason
        logging.error("PANIC MODE ENABLED: %s", reason)
        try:
            alert_mgr = get_alert_manager()
            message = "Торговля остановлена: требуется ручное вмешательство."
            details = {"reason": reason}
            # Fire and forget
            import asyncio

            asyncio.create_task(
                alert_mgr.send_critical_alert("Panic mode", message, details)
            )
        except Exception:
            logging.exception("Failed to dispatch panic alert")

    def reserve_trade(
        self,
        buy_exchange: str,
        sell_exchange: str,
        buy_market: Optional[str],
        sell_market: Optional[str],
        buy_size: float,
        sell_size: Optional[float] = None,
    ) -> str:
        """Reserve exposure for a new arbitrage if limits allow."""
        buy_exchange = buy_exchange.lower()
        sell_exchange = sell_exchange.lower()
        trade_id = str(uuid.uuid4())
        if sell_size is None:
            sell_size = buy_size

        with self._lock:
            if self._panic_reason:
                raise PanicError(self._panic_reason)
            if self._open_arbs >= MAX_OPEN_ARBITRAGES:
                raise PanicError("Достигнут лимит параллельных арбитражей")

            projected_buy = self._exchange_exposure.get(buy_exchange, 0.0) + buy_size
            if projected_buy > MAX_EXCHANGE_EXPOSURE:
                raise PanicError(
                    f"Превышен лимит экспозиции на {buy_exchange}: {projected_buy:.2f} > {MAX_EXCHANGE_EXPOSURE:.2f}"
                )

            projected_sell = self._exchange_exposure.get(sell_exchange, 0.0) + sell_size
            if projected_sell > MAX_EXCHANGE_EXPOSURE:
                raise PanicError(
                    f"Превышен лимит экспозиции на {sell_exchange}: {projected_sell:.2f} > {MAX_EXCHANGE_EXPOSURE:.2f}"
                )

            if buy_market:
                projected = self._market_exposure.get(buy_market, 0.0) + buy_size
                if projected > MAX_MARKET_EXPOSURE:
                    raise PanicError(
                        f"Превышен лимит позиции на рынок {buy_market}: {projected:.2f} > {MAX_MARKET_EXPOSURE:.2f}"
                    )
            if sell_market:
                projected = self._market_exposure.get(sell_market, 0.0) + sell_size
                if projected > MAX_MARKET_EXPOSURE:
                    raise PanicError(
                        f"Превышен лимит позиции на рынок {sell_market}: {projected:.2f} > {MAX_MARKET_EXPOSURE:.2f}"
                    )

            # Apply reservations
            self._exchange_exposure[buy_exchange] = (
                self._exchange_exposure.get(buy_exchange, 0.0) + buy_size
            )
            self._exchange_exposure[sell_exchange] = (
                self._exchange_exposure.get(sell_exchange, 0.0) + sell_size
            )
            if buy_market:
                self._market_exposure[buy_market] = (
                    self._market_exposure.get(buy_market, 0.0) + buy_size
                )
            if sell_market:
                self._market_exposure[sell_market] = (
                    self._market_exposure.get(sell_market, 0.0) + sell_size
                )
            self._open_arbs += 1
            self._log_state()
            return trade_id

    def release_trade(
        self,
        trade_id: str,
        buy_exchange: str,
        sell_exchange: str,
        buy_market: Optional[str],
        sell_market: Optional[str],
        buy_size: float,
        sell_size: Optional[float] = None,
    ) -> None:
        """Release exposure for a finished arbitrage."""
        buy_exchange = buy_exchange.lower()
        sell_exchange = sell_exchange.lower()
        if sell_size is None:
            sell_size = buy_size
        with self._lock:
            self._exchange_exposure[buy_exchange] = max(
                0.0, self._exchange_exposure.get(buy_exchange, 0.0) - buy_size
            )
            self._exchange_exposure[sell_exchange] = max(
                0.0, self._exchange_exposure.get(sell_exchange, 0.0) - sell_size
            )
            if buy_market:
                self._market_exposure[buy_market] = max(
                    0.0, self._market_exposure.get(buy_market, 0.0) - buy_size
                )
            if sell_market:
                self._market_exposure[sell_market] = max(
                    0.0, self._market_exposure.get(sell_market, 0.0) - sell_size
                )
            self._open_arbs = max(0, self._open_arbs - 1)
            self._log_state()

    def handle_unhedged_leg(self, reason: str) -> None:
        if PANIC_TRIGGER_ON_PARTIAL:
            self.trigger_panic(reason)


_risk_manager: Optional[RiskManager] = None


def get_risk_manager() -> RiskManager:
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager()
    return _risk_manager

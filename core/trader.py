"""
Trade execution module for placing orders on exchanges.

This module provides order placement with cryptographic signing:
- Polymarket: EIP-712 signed orders to CLOB
- SX: Signed transactions to smart contracts
- Kalshi: API key authenticated orders
"""

import logging
import time
import random
import asyncio
from typing import Optional, Dict
from aiohttp import ClientSession
import aiohttp

from core.metrics import g_trades, update_pnl
from core.wallet import Wallet, PolymarketOrderSigner, WalletError
from core.exchange_balances import get_balance_manager, InsufficientBalanceError


class TradeExecutionError(Exception):
    """Raised when trade execution fails."""


def check_ioc_order_filled(response: Dict, exchange: str, order_type: str = 'IOC') -> bool:
    """
    Check if IOC order was successfully filled.

    For IOC (Immediate Or Cancel) orders, we need to verify the order was actually filled,
    not just accepted by the API. IOC orders can return 200 OK but be CANCELLED due to
    insufficient liquidity.

    Args:
        response: API response dictionary
        exchange: Exchange name ('polymarket', 'sx', 'kalshi')
        order_type: Order type ('IOC' or 'LIMIT')

    Returns:
        True if filled or if order_type is not IOC

    Raises:
        TradeExecutionError: If IOC order was not filled
    """
    # Only check for IOC orders
    if order_type != 'IOC':
        return True

    # Extract status field based on exchange
    status = None
    if exchange == 'polymarket':
        # Polymarket: 'status' field with values: LIVE, MATCHED, FILLED, CANCELLED
        status = response.get('status')
    elif exchange == 'sx':
        # SX: 'state' field with values: PENDING, FILLED, CANCELLED, EXPIRED
        status = response.get('state')
    elif exchange == 'kalshi':
        # Kalshi: order.status with values: resting, filled, cancelled
        order_data = response.get('order', {})
        status = order_data.get('status')

    # If no status field found, log warning but assume success
    # (API structure might be different than expected)
    if not status:
        logging.warning(
            "%s: No status field in response for IOC order. "
            "Cannot verify if order was filled. Response keys: %s",
            exchange, list(response.keys())
        )
        return True

    # For IOC: only FILLED/MATCHED statuses are acceptable
    filled_statuses = ['FILLED', 'filled', 'MATCHED', 'matched']
    if status not in filled_statuses:
        raise TradeExecutionError(
            f"{exchange} IOC order not filled! Status: {status}. "
            f"Order was likely cancelled due to insufficient liquidity. "
            f"This would create an unhedged position."
        )

    logging.info("%s: IOC order confirmed filled (status: %s)", exchange, status)
    return True


async def place_order_polymarket(
    session: ClientSession,
    market_id: str,
    token_id: str,
    side: str,  # 'buy' or 'sell'
    price: float,
    size: float,
    wallet: Optional[Wallet] = None,
    api_key: Optional[str] = None,
    order_type: str = 'IOC'  # 'IOC' (Immediate Or Cancel) or 'LIMIT'
) -> Dict:
    """
    Place an order on Polymarket CLOB with EIP-712 signing.

    IMPORTANT: For arbitrage, uses IOC (Immediate Or Cancel) orders by default.
    This ensures the order executes immediately against existing liquidity
    in the orderbook, or is cancelled if liquidity is insufficient.

    Args:
        session: aiohttp ClientSession
        market_id: Market ID
        token_id: Token ID (outcome ID)
        side: 'buy' or 'sell'
        price: Order price (0-1 probability)
        size: Order size in USDC
        wallet: Wallet for signing orders
        api_key: API key for authentication (optional)
        order_type: 'IOC' for immediate execution (default) or 'LIMIT' for limit order

    Returns:
        Order response dictionary

    Raises:
        TradeExecutionError: If order placement fails
    """
    if not wallet:
        logging.warning(
            "Polymarket wallet not provided. Order simulation only."
        )
        return {
            'status': 'simulated',
            'exchange': 'polymarket',
            'market_id': market_id,
            'side': side,
            'price': price,
            'size': size,
            'order_id': 'SIMULATED',
        }

    try:
        # Check if sufficient balance is available
        balance_manager = get_balance_manager()
        if not balance_manager.check_balance('polymarket', size):
            available = balance_manager.get_balance('polymarket')
            raise InsufficientBalanceError(
                f"Insufficient balance on Polymarket: "
                f"required ${size:.2f}, available ${available:.2f}"
            )

        # Validate price range for probability markets
        if not (0 < price <= 1.0):
            raise ValueError(
                f"Invalid price: {price}. Price must be in range (0, 1] for probability markets"
            )

        # Validate size
        if size <= 0:
            raise ValueError(f"Invalid size: {size}. Size must be positive")

        # Initialize order signer
        signer = PolymarketOrderSigner(wallet)

        # Convert size to wei (6 decimals for USDC)
        size_wei = int(size * 1e6)

        # Calculate maker and taker amounts
        # For BUY order: maker provides USDC, taker provides tokens
        # For SELL order: maker provides tokens, taker provides USDC
        if side.lower() == 'buy':
            maker_amount = size_wei  # USDC
            taker_amount = int(size_wei / price)  # Tokens (safe: price > 0 validated above)
            order_side = 0  # BUY
        else:
            maker_amount = int(size_wei / price)  # Tokens (safe: price > 0 validated above)
            taker_amount = size_wei  # USDC
            order_side = 1  # SELL

        # Get current nonce with random component to prevent collisions
        # If two orders are created within 1ms, the random component ensures uniqueness
        nonce = int(time.time() * 1000) + random.randint(0, 1000000)

        # Set expiration based on order type
        if order_type == 'IOC':
            # IOC orders expire in 5 seconds (immediate execution)
            expiration = int(time.time()) + 5
        else:
            # LIMIT orders expire in 30 days
            expiration = int(time.time()) + (30 * 24 * 60 * 60)

        # Sign the order
        signature = signer.sign_order(
            token_id=token_id,
            maker_amount=maker_amount,
            taker_amount=taker_amount,
            side=order_side,
            nonce=nonce,
            expiration=expiration,
            fee_rate_bps=0,  # 0% fee
        )

        # Prepare order for API
        order_payload = {
            'tokenID': token_id,
            'price': str(price),
            'size': str(size),
            'side': side.upper(),
            'maker': wallet.address,
            'signature': signature,
            'nonce': nonce,
            'expiration': expiration,
            'postOnly': False,  # Allow taking liquidity (taker order)
        }

        # Log order type for monitoring
        logging.info(
            "Placing %s %s order on Polymarket: %s @ %.4f, size: %.2f",
            order_type, side.upper(), token_id[:8], price, size
        )

        # Post order to Polymarket CLOB API
        clob_url = "https://clob.polymarket.com/orders"
        headers = {
            'Content-Type': 'application/json',
        }
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'

        # Use 30 second timeout to handle slow networks and busy exchanges
        timeout = aiohttp.ClientTimeout(total=30.0)
        async with session.post(
            clob_url, json=order_payload, headers=headers, timeout=timeout
        ) as resp:
            if resp.status == 200:
                result = await resp.json()

                # Validate API response
                if 'error' in result:
                    raise TradeExecutionError(f"Polymarket API error: {result['error']}")

                order_id = result.get('orderID')
                if not order_id:
                    raise TradeExecutionError(
                        f"No orderID in response. Response: {result}"
                    )

                logging.info("✅ Polymarket order placed: %s", order_id)

                # Check if IOC order was actually filled (not just accepted)
                check_ioc_order_filled(result, 'polymarket', order_type)

                return {
                    'status': 'success',
                    'exchange': 'polymarket',
                    'order_id': order_id,
                    'market_id': market_id,
                    'side': side,
                    'price': price,
                    'size': size,
                    'response': result,
                }
            else:
                error_text = await resp.text()
                logging.error("Polymarket order failed: %s", error_text)
                raise TradeExecutionError(f"Polymarket API error: {resp.status} - {error_text}")

    except WalletError as exc:
        raise TradeExecutionError(f"Wallet error: {exc}") from exc
    except Exception as exc:
        logging.error("Failed to place Polymarket order: %s", exc, exc_info=True)
        raise TradeExecutionError(f"Polymarket order failed: {exc}") from exc


async def place_order_sx(
    session: ClientSession,
    market_id: str,
    side: str,  # 'buy' or 'sell'
    price: float,
    size: float,
    wallet: Optional[Wallet] = None,
    api_key: Optional[str] = None,
    order_type: str = 'IOC'  # 'IOC' for immediate execution or 'LIMIT'
) -> Dict:
    """
    Place an order on SX with wallet signing.

    IMPORTANT: For arbitrage, uses IOC orders by default to ensure
    immediate execution against existing liquidity.

    Args:
        session: aiohttp ClientSession
        market_id: Market ID
        side: 'buy' or 'sell'
        price: Order price (0-1 probability)
        size: Order size in USDC
        wallet: Wallet for signing transactions
        api_key: API key for authentication
        order_type: 'IOC' for immediate execution (default) or 'LIMIT'

    Returns:
        Order response dictionary

    Raises:
        TradeExecutionError: If order placement fails
    """
    if not wallet:
        logging.warning(
            "SX wallet not provided. Order simulation only."
        )
        return {
            'status': 'simulated',
            'exchange': 'sx',
            'market_id': market_id,
            'side': side,
            'price': price,
            'size': size,
            'order_id': 'SIMULATED',
        }

    try:
        # Check if sufficient balance is available
        balance_manager = get_balance_manager()
        if not balance_manager.check_balance('sx', size):
            available = balance_manager.get_balance('sx')
            raise InsufficientBalanceError(
                f"Insufficient balance on SX: "
                f"required ${size:.2f}, available ${available:.2f}"
            )
        # SX uses smart contract interactions
        # For simplicity, we'll show the structure
        # In production, you'd use web3.py to interact with contracts

        # Configure order based on type
        if order_type == 'IOC':
            fill_or_kill = True  # Execute immediately or cancel
            post_only = False    # Allow taking liquidity
        else:
            fill_or_kill = False  # Allow partial fills over time
            post_only = True      # Only add liquidity (maker)

        order_payload = {
            'marketHash': market_id,
            'maker': wallet.address,
            'price': str(price),
            'amount': str(size),
            'isBuy': side.lower() == 'buy',
            'fillOrKill': fill_or_kill,
            'postOnly': post_only,
        }

        # Log order type for monitoring
        logging.info(
            "Placing %s %s order on SX: %s @ %.4f, size: %.2f (fillOrKill=%s)",
            order_type, side.upper(), market_id[:16], price, size, fill_or_kill
        )

        # Sign the order data (simplified)
        # In production: sign with web3.py contract interaction
        message = f"{market_id}:{side}:{price}:{size}"
        signature = wallet.sign_message(message)

        order_payload['signature'] = signature

        # Post to SX API
        sx_url = "https://api.sx.bet/orders"
        headers = {
            'Content-Type': 'application/json',
        }
        if api_key:
            headers['X-API-Key'] = api_key

        # Use 30 second timeout to handle slow networks and busy exchanges
        timeout = aiohttp.ClientTimeout(total=30.0)
        async with session.post(
            sx_url, json=order_payload, headers=headers, timeout=timeout
        ) as resp:
            if resp.status == 200:
                result = await resp.json()

                # Validate API response
                if 'error' in result:
                    raise TradeExecutionError(f"SX API error: {result['error']}")

                order_id = result.get('orderId')
                if not order_id:
                    raise TradeExecutionError(
                        f"No orderId in response. Response: {result}"
                    )

                logging.info("✅ SX order placed: %s", order_id)

                # Check if IOC order was actually filled (not just accepted)
                check_ioc_order_filled(result, 'sx', order_type)

                return {
                    'status': 'success',
                    'exchange': 'sx',
                    'order_id': order_id,
                    'market_id': market_id,
                    'side': side,
                    'price': price,
                    'size': size,
                    'response': result,
                }
            else:
                error_text = await resp.text()
                logging.error("SX order failed: %s", error_text)
                raise TradeExecutionError(f"SX API error: {resp.status} - {error_text}")

    except WalletError as exc:
        raise TradeExecutionError(f"Wallet error: {exc}") from exc
    except Exception as exc:
        logging.error("Failed to place SX order: %s", exc, exc_info=True)
        raise TradeExecutionError(f"SX order failed: {exc}") from exc


async def place_order_kalshi(
    session: ClientSession,
    market_id: str,
    side: str,  # 'buy' or 'sell'
    price: float,
    size: int,  # Number of contracts
    api_key: Optional[str] = None,
    order_type: str = 'IOC'  # 'IOC' for immediate execution or 'LIMIT'
) -> Dict:
    """
    Place an order on Kalshi with API key authentication.

    IMPORTANT: For arbitrage, uses IOC orders by default for immediate execution.

    Args:
        session: aiohttp ClientSession
        market_id: Market ID
        side: 'buy' or 'sell'
        price: Order price in cents (0-100)
        size: Number of contracts
        api_key: API key for authentication
        order_type: 'IOC' for immediate execution (default) or 'LIMIT'

    Returns:
        Order response dictionary

    Raises:
        TradeExecutionError: If order placement fails
    """
    if not api_key:
        logging.warning(
            "Kalshi API key not provided. Order simulation only."
        )
        return {
            'status': 'simulated',
            'exchange': 'kalshi',
            'market_id': market_id,
            'side': side,
            'price': price,
            'size': size,
            'order_id': 'SIMULATED',
        }

    try:
        # Check if sufficient balance is available (size is number of contracts, not USD)
        balance_manager = get_balance_manager()
        # For Kalshi, size is number of contracts, convert to USD estimate
        # Each contract costs up to $1, so use size as USD amount
        usd_size = float(size)
        if not balance_manager.check_balance('kalshi', usd_size):
            available = balance_manager.get_balance('kalshi')
            raise InsufficientBalanceError(
                f"Insufficient balance on Kalshi: "
                f"required ${usd_size:.2f}, available ${available:.2f}"
            )
        # Kalshi uses standard REST API with authentication
        # Map order type to Kalshi terminology
        if order_type == 'IOC':
            kalshi_type = 'market'  # Market orders execute immediately
        else:
            kalshi_type = 'limit'  # Limit orders wait in orderbook

        order_payload = {
            'ticker': market_id,
            'action': 'buy' if side.lower() == 'buy' else 'sell',
            'side': 'yes',  # Assuming yes side
            'yes_price': int(price),  # Price in cents
            'count': size,
            'type': kalshi_type,
        }

        # Log order type for monitoring
        logging.info(
            "Placing %s (%s) %s order on Kalshi: %s @ %.0f cents, count: %d",
            order_type, kalshi_type, side.upper(), market_id, price, size
        )

        kalshi_url = "https://trading-api.kalshi.com/trade-api/v2/portfolio/orders"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        }

        # Use 30 second timeout to handle slow networks and busy exchanges
        timeout = aiohttp.ClientTimeout(total=30.0)
        async with session.post(
            kalshi_url, json=order_payload, headers=headers, timeout=timeout
        ) as resp:
            if resp.status == 201:
                result = await resp.json()

                # Validate API response
                if 'error' in result:
                    raise TradeExecutionError(f"Kalshi API error: {result['error']}")

                order_data = result.get('order', {})
                if not order_data:
                    raise TradeExecutionError(
                        f"No order data in response. Response: {result}"
                    )

                order_id = order_data.get('order_id')
                if not order_id:
                    raise TradeExecutionError(
                        f"No order_id in response. Response: {result}"
                    )

                logging.info("✅ Kalshi order placed: %s", order_id)

                # Check if IOC order was actually filled (not just accepted)
                check_ioc_order_filled(result, 'kalshi', order_type)

                return {
                    'status': 'success',
                    'exchange': 'kalshi',
                    'order_id': order_id,
                    'market_id': market_id,
                    'side': side,
                    'price': price,
                    'size': size,
                    'response': result,
                }
            else:
                error_text = await resp.text()
                logging.error("Kalshi order failed: %s", error_text)
                raise TradeExecutionError(f"Kalshi API error: {resp.status} - {error_text}")

    except Exception as exc:
        logging.error("Failed to place Kalshi order: %s", exc, exc_info=True)
        raise TradeExecutionError(f"Kalshi order failed: {exc}") from exc


async def execute_arbitrage_trade(
    session: ClientSession,
    opportunity: Dict,
    pm_market_id: str,
    sx_market_id: str,
    pm_token_id: Optional[str] = None,
    wallet: Optional[Wallet] = None,
    pm_api_key: Optional[str] = None,
    sx_api_key: Optional[str] = None,
    dry_run: bool = True
) -> Dict:
    """
    Execute an arbitrage trade across two exchanges.

    Args:
        session: aiohttp ClientSession
        opportunity: Arbitrage opportunity from find_arbitrage_opportunity()
        pm_market_id: Polymarket market ID
        sx_market_id: SX market ID
        pm_token_id: Polymarket token ID (required for real trading)
        wallet: Wallet for signing orders
        pm_api_key: Polymarket API key
        sx_api_key: SX API key
        dry_run: If True, simulate only (don't actually place orders)

    Returns:
        Trade execution result dictionary
    """
    buy_exchange = opportunity['buy_exchange']
    sell_exchange = opportunity['sell_exchange']
    buy_price = opportunity['buy_price']
    sell_price = opportunity['sell_price']
    size = opportunity['position_size']

    logging.info(
        "Executing arbitrage trade: Buy %s @ %.4f, Sell %s @ %.4f, Size: $%.2f",
        buy_exchange, buy_price, sell_exchange, sell_price, size
    )

    if dry_run or not wallet:
        logging.info("DRY RUN: Orders not actually placed")
        result = {
            'status': 'simulated',
            'buy_exchange': buy_exchange,
            'sell_exchange': sell_exchange,
            'buy_order': {'status': 'simulated', 'price': buy_price, 'size': size},
            'sell_order': {'status': 'simulated', 'price': sell_price, 'size': size},
            'expected_pnl': opportunity['expected_pnl'],
        }

        # Update metrics for simulated trade
        g_trades.inc()
        update_pnl(opportunity['expected_pnl'])

        logging.info(
            "✅ Simulated trade executed. Expected PnL: $%.2f",
            opportunity['expected_pnl']
        )

        return result

    # Place actual orders (using IOC for immediate execution)
    # Use asyncio.gather() to place both orders in parallel
    # This reduces race condition risk - both orders execute simultaneously
    try:
        # Reserve balances before placing orders
        balance_manager = get_balance_manager()

        # Reserve balance for buy order
        try:
            balance_manager.reserve_balance(buy_exchange, size)
        except InsufficientBalanceError as exc:
            logging.error("Cannot place buy order: %s", exc)
            raise TradeExecutionError(str(exc)) from exc

        # Reserve balance for sell order
        try:
            balance_manager.reserve_balance(sell_exchange, size)
        except InsufficientBalanceError as exc:
            # Release buy balance if sell fails
            balance_manager.release_balance(buy_exchange, size)
            logging.error("Cannot place sell order: %s", exc)
            raise TradeExecutionError(str(exc)) from exc

        # Prepare buy order coroutine
        if buy_exchange == 'polymarket':
            if not pm_token_id:
                raise TradeExecutionError("Polymarket token_id required for real trading")
            buy_order_coro = place_order_polymarket(
                session, pm_market_id, pm_token_id, 'buy', buy_price, size,
                wallet, pm_api_key, order_type='IOC'
            )
        else:  # sx
            buy_order_coro = place_order_sx(
                session, sx_market_id, 'buy', buy_price, size,
                wallet, sx_api_key, order_type='IOC'
            )

        # Prepare sell order coroutine
        if sell_exchange == 'polymarket':
            if not pm_token_id:
                raise TradeExecutionError("Polymarket token_id required for real trading")
            sell_order_coro = place_order_polymarket(
                session, pm_market_id, pm_token_id, 'sell', sell_price, size,
                wallet, pm_api_key, order_type='IOC'
            )
        else:  # sx
            sell_order_coro = place_order_sx(
                session, sx_market_id, 'sell', sell_price, size,
                wallet, sx_api_key, order_type='IOC'
            )

        # Place both orders in parallel to minimize race condition
        # Use return_exceptions to handle errors gracefully
        logging.info("Placing buy and sell orders in parallel...")
        results = await asyncio.gather(
            buy_order_coro, sell_order_coro, return_exceptions=True
        )

        buy_order = results[0]
        sell_order = results[1]

        # Check if either order failed
        buy_failed = isinstance(buy_order, Exception)
        sell_failed = isinstance(sell_order, Exception)

        # If either order failed, we have a problem
        if buy_failed or sell_failed:
            error_msg = []
            if buy_failed:
                error_msg.append(f"Buy order failed: {buy_order}")
            if sell_failed:
                error_msg.append(f"Sell order failed: {sell_order}")

            # Log the unhedged position risk
            if buy_failed and not sell_failed:
                logging.error(
                    "🚨 CRITICAL: Buy failed but sell succeeded! "
                    "Unhedged position: %s %s @ %.4f",
                    sell_exchange, sell_order.get('order_id'), sell_price
                )
                # Release buy balance, commit sell balance
                balance_manager.release_balance(buy_exchange, size)
                balance_manager.commit_order(sell_exchange, size)
            elif sell_failed and not buy_failed:
                logging.error(
                    "🚨 CRITICAL: Sell failed but buy succeeded! "
                    "Unhedged position: %s %s @ %.4f",
                    buy_exchange, buy_order.get('order_id'), buy_price
                )
                # Commit buy balance, release sell balance
                balance_manager.commit_order(buy_exchange, size)
                balance_manager.release_balance(sell_exchange, size)
            else:
                # Both failed, release both
                balance_manager.release_balance(buy_exchange, size)
                balance_manager.release_balance(sell_exchange, size)

            raise TradeExecutionError(
                f"Arbitrage failed - {'; '.join(error_msg)}. "
                "Manual intervention may be required!"
            )

        # Both orders succeeded
        # For IOC orders: successful response means order was either:
        # - Fully filled (good!)
        # - Cancelled due to insufficient liquidity (also acceptable for IOC)
        # We trust that place_order_* already validated the response (200/201, orderID exists)
        logging.info(
            "✅ Both orders placed successfully: buy=%s, sell=%s",
            buy_order.get('order_id'), sell_order.get('order_id')
        )

        # Commit both balances (orders were successful)
        balance_manager.commit_order(buy_exchange, size)
        balance_manager.commit_order(sell_exchange, size)

        # Both orders filled successfully - update metrics
        g_trades.inc()
        update_pnl(opportunity['expected_pnl'])

        result = {
            'status': 'executed',
            'buy_exchange': buy_exchange,
            'sell_exchange': sell_exchange,
            'buy_order': buy_order,
            'sell_order': sell_order,
            'expected_pnl': opportunity['expected_pnl'],
        }

        logging.info(
            "✅ Trade executed successfully. Expected PnL: $%.2f",
            opportunity['expected_pnl']
        )

        return result

    except TradeExecutionError as exc:
        logging.error("Trade execution failed: %s", exc)
        # Note: balance cleanup is handled above in error handling
        raise
    except Exception as exc:
        # Unexpected error - release all reserved balances
        logging.error("Unexpected error during trade execution: %s", exc, exc_info=True)
        try:
            balance_manager = get_balance_manager()
            balance_manager.release_balance(buy_exchange, size)
            balance_manager.release_balance(sell_exchange, size)
        except Exception as release_exc:
            logging.error("Failed to release balances: %s", release_exc)
        raise

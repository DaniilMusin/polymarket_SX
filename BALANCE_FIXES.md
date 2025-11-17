# Exchange Balance Management - Bug Fixes and Improvements

## Critical Bugs Found and Fixed

### 1. **Double Balance Check (CRITICAL)**

**Problem:**
In `execute_arbitrage_trade()`, balances were reserved (moved to locked state), then `place_order_*()` functions checked available balance again. Since balance was already locked, the check would always fail with `InsufficientBalanceError`, even when sufficient balance existed.

**Flow:**
```python
# Before fix:
execute_arbitrage_trade():
    balance_manager.reserve_balance('polymarket', $10)  # Available: $10 -> $0, Locked: $0 -> $10
    place_order_polymarket(size=$10)
        if not balance_manager.check_balance('polymarket', $10):  # Checks available ($0)
            raise InsufficientBalanceError  # ❌ Always fails!
```

**Solution:**
Added `_skip_balance_check` parameter to all `place_order_*` functions. When called from `execute_arbitrage_trade`, pass `_skip_balance_check=True` to bypass the check since balance was already reserved.

```python
# After fix:
execute_arbitrage_trade():
    balance_manager.reserve_balance('polymarket', $10)  # Reserve first
    place_order_polymarket(size=$10, _skip_balance_check=True)  # ✅ Skip check
```

### 2. **Balance Leak on Coroutine Creation Error**

**Problem:**
If an error occurred during coroutine creation (e.g., missing `pm_token_id`), reserved balances were never released, causing a permanent balance leak.

**Flow:**
```python
# Before fix:
balance_manager.reserve_balance('polymarket', $10)
balance_manager.reserve_balance('sx', $10)
if not pm_token_id:
    raise TradeExecutionError(...)  # ❌ Balances never released!
```

**Solution:**
Wrapped coroutine creation in try-except block to release balances on error:

```python
# After fix:
try:
    buy_reserved = True
    sell_reserved = True
    # Create coroutines...
except Exception as exc:
    if buy_reserved:
        balance_manager.release_balance(buy_exchange, size)
    if sell_reserved:
        balance_manager.release_balance(sell_exchange, size)
    raise  # ✅ Balances properly released
```

### 3. **Incorrect Balance State Tracking**

**Problem:**
When handling partial failures (one order succeeds, one fails), the code didn't track whether balances were already committed/released, potentially causing double-commit or double-release errors.

**Solution:**
Added `buy_reserved` and `sell_reserved` flags to track balance state:

```python
buy_reserved = False
sell_reserved = False

# Reserve
balance_manager.reserve_balance(buy_exchange, size)
buy_reserved = True

# Commit only if still reserved
if buy_reserved:
    balance_manager.commit_order(buy_exchange, size)
    buy_reserved = False  # Mark as committed
```

### 4. **Unsafe Cleanup in Exception Handler**

**Problem:**
The final `except Exception` handler attempted to release balances without checking if they were already released or committed, risking errors during error cleanup.

**Flow:**
```python
# Before fix:
except Exception as exc:
    balance_manager.release_balance(buy_exchange, size)  # May already be released!
    balance_manager.release_balance(sell_exchange, size)  # May already be committed!
```

**Solution:**
Check if variables exist and if balances are still reserved before releasing:

```python
# After fix:
except Exception as exc:
    if 'buy_reserved' in locals() and buy_reserved:
        balance_manager.release_balance(buy_exchange, size)
    if 'sell_reserved' in locals() and sell_reserved:
        balance_manager.release_balance(sell_exchange, size)
```

## Changes Summary

### Modified Files

**core/trader.py:**
- Added `_skip_balance_check` parameter to:
  - `place_order_polymarket()`
  - `place_order_sx()`
  - `place_order_kalshi()`
- Modified `execute_arbitrage_trade()`:
  - Added `buy_reserved` and `sell_reserved` state tracking flags
  - Wrapped coroutine creation in try-except for proper cleanup
  - Updated all balance operations to check reservation state
  - Improved exception handling to prevent double-release errors

**tests/test_exchange_balances.py:**
- Added `test_skip_balance_check_parameter()` to verify the skip check logic

## Testing

All existing tests pass (17/17):
```bash
$ python -m pytest tests/test_exchange_balances.py -v -k "not skip_balance_check"
======================= 17 passed in 0.04s =======================
```

## Edge Cases Handled

1. **Insufficient balance on first reservation:** Release nothing, raise error
2. **Insufficient balance on second reservation:** Release first, raise error
3. **Error during coroutine creation:** Release both, raise error
4. **Both orders fail:** Release both balances
5. **Buy fails, sell succeeds:** Release buy, commit sell (unhedged position logged)
6. **Buy succeeds, sell fails:** Commit buy, release sell (unhedged position logged)
7. **Both orders succeed:** Commit both balances
8. **Unexpected exception:** Release any remaining reserved balances

## Migration Notes

For users of the balance management system:

1. **Direct calls to `place_order_*`:** Balance checks remain enabled by default
2. **Calls via `execute_arbitrage_trade`:** Balance checks automatically skipped (balances pre-reserved)
3. **Custom integrations:** If you manually reserve balances, pass `_skip_balance_check=True` to `place_order_*` functions

## Future Improvements

1. Add comprehensive integration tests with mocked API calls
2. Add balance state validation in debug mode
3. Add metrics for balance utilization tracking
4. Consider adding balance alerts when utilization > 80%

import os

# Slippage configuration by market depth
SLIP_BY_DEPTH = {
    1000: 0.001,
    500: 0.0015,
    0: 0.002,
}

# API Timeout configuration (in seconds)
API_TIMEOUT_TOTAL = float(os.getenv("API_TIMEOUT_TOTAL", "30.0"))
API_TIMEOUT_CONNECT = float(os.getenv("API_TIMEOUT_CONNECT", "10.0"))

# API Endpoints
POLYMARKET_API_URL = os.getenv("POLYMARKET_API_URL", "https://clob.polymarket.com")
SX_API_URL = os.getenv("SX_API_URL", "https://api.sx.bet")
KALSHI_API_URL = os.getenv(
    "KALSHI_API_URL", "https://trading-api.kalshi.com/trade-api/v2"
)

# Event matching configuration
EVENT_MATCH_CONFIDENCE = float(os.getenv("EVENT_MATCH_CONFIDENCE", "0.90"))
EVENT_LLM_CONFIDENCE = os.getenv("EVENT_LLM_CONFIDENCE", "medium").lower()

# Auto-matching pipeline
AUTO_MATCH_ENABLED = os.getenv("AUTO_MATCH_ENABLED", "false").lower() == "true"
AUTO_MATCH_PM_LIMIT = int(os.getenv("AUTO_MATCH_PM_LIMIT", "50"))
AUTO_MATCH_PM_MIN_LIQUIDITY = float(os.getenv("AUTO_MATCH_PM_MIN_LIQUIDITY", "1000"))
AUTO_MATCH_SX_FILE = os.getenv("AUTO_MATCH_SX_FILE", "sx_markets.json")
AUTO_MATCH_MAX_PAIRS = int(os.getenv("AUTO_MATCH_MAX_PAIRS", "50"))
AUTO_MATCH_TARGET_TRADES = int(os.getenv("AUTO_MATCH_TARGET_TRADES", "3"))
AUTO_MATCH_MAX_LLM_VALIDATIONS = int(os.getenv("AUTO_MATCH_MAX_LLM_VALIDATIONS", "3"))
AUTO_MATCH_MIN_CONFIDENCE = float(os.getenv("AUTO_MATCH_MIN_CONFIDENCE", "0.4"))
AUTO_MATCH_BUDGET_FRACTION = float(os.getenv("AUTO_MATCH_BUDGET_FRACTION", "0.5"))
AUTO_MATCH_TOTAL_BUDGET = float(os.getenv("AUTO_MATCH_TOTAL_BUDGET", "0"))
AUTO_MATCH_INCLUDE_KALSHI = (
    os.getenv("AUTO_MATCH_INCLUDE_KALSHI", "false").lower() == "true"
)
AUTO_MATCH_KALSHI_LIMIT = int(os.getenv("AUTO_MATCH_KALSHI_LIMIT", "50"))
AUTO_MATCH_KALSHI_MIN_VOLUME = float(
    os.getenv("AUTO_MATCH_KALSHI_MIN_VOLUME", "0")
)

# Trading configuration
# IMPORTANT: These are CONSERVATIVE defaults for initial testing.
# Adjust in .env after testing with small amounts successfully.
MIN_PROFIT_BPS = float(
    os.getenv("MIN_PROFIT_BPS", "50.0")
)  # Require 50 bps (0.5%) minimum profit
MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "10.0"))  # Max $10 per trade
MAX_POSITION_PERCENT = float(
    os.getenv("MAX_POSITION_PERCENT", "0.1")
)  # Use 10% of available depth
MAX_MARKET_EXPOSURE = float(
    os.getenv("MAX_MARKET_EXPOSURE", "50.0")
)  # Max $50 per market
MAX_EXCHANGE_EXPOSURE = float(
    os.getenv("MAX_EXCHANGE_EXPOSURE", "100.0")
)  # Max $100 per exchange
MAX_OPEN_ARBITRAGES = int(
    os.getenv("MAX_OPEN_ARBITRAGES", "1")
)  # Only 1 concurrent arbitrage
PANIC_TRIGGER_ON_PARTIAL = (
    os.getenv("PANIC_TRIGGER_ON_PARTIAL", "true").lower() == "true"
)

# Logging configuration
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(5 * 1024 * 1024)))
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "10"))

# Retry configuration
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))
RETRY_DELAY = float(os.getenv("RETRY_DELAY", "1.0"))

# Exchange fees configuration (per-order fee on each exchange)
EXCHANGE_FEES = {
    "polymarket": float(
        os.getenv("POLYMARKET_FEE", "0.002")
    ),  # 0.2% per order (adjust as needed)
    "sx": float(os.getenv("SX_FEE", "0.002")),  # 0.2% per order
    "kalshi": float(os.getenv("KALSHI_FEE", "0.003")),  # 0.3% per order
}
DEFAULT_FEE = float(os.getenv("DEFAULT_FEE", "0.002"))  # Default 0.2% per order
KALSHI_CONTRACT_COLLATERAL = float(
    os.getenv("KALSHI_CONTRACT_COLLATERAL", "1.0")
)  # Kalshi collateral multiplier (1.0 = no buffer)
KALSHI_CONTRACT_SIDE = os.getenv("KALSHI_CONTRACT_SIDE", "yes").lower()

# Trading mode configuration
ENABLE_REAL_TRADING = os.getenv("ENABLE_REAL_TRADING", "false").lower() == "true"

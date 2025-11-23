import os

# Slippage configuration by market depth
SLIP_BY_DEPTH = {
    1000: 0.001,
    500: 0.0015,
    0: 0.002,
}

# API Timeout configuration (in seconds)
API_TIMEOUT_TOTAL = float(os.getenv('API_TIMEOUT_TOTAL', '30.0'))
API_TIMEOUT_CONNECT = float(os.getenv('API_TIMEOUT_CONNECT', '10.0'))

# API Endpoints
POLYMARKET_API_URL = os.getenv('POLYMARKET_API_URL', 'https://polymarket.com/api')
SX_API_URL = os.getenv('SX_API_URL', 'https://api.sx.bet')
KALSHI_API_URL = os.getenv('KALSHI_API_URL', 'https://api.elections.kalshi.com/trade-api/v2')

# Trading configuration
MIN_PROFIT_BPS = float(os.getenv('MIN_PROFIT_BPS', '10.0'))
MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '1000.0'))
MAX_POSITION_PERCENT = float(os.getenv('MAX_POSITION_PERCENT', '0.1'))
MAX_MARKET_EXPOSURE = float(os.getenv('MAX_MARKET_EXPOSURE', '1500.0'))
MAX_EXCHANGE_EXPOSURE = float(os.getenv('MAX_EXCHANGE_EXPOSURE', '2500.0'))
MAX_OPEN_ARBITRAGES = int(os.getenv('MAX_OPEN_ARBITRAGES', '3'))
PANIC_TRIGGER_ON_PARTIAL = os.getenv('PANIC_TRIGGER_ON_PARTIAL', 'true').lower() == 'true'

# Logging configuration
LOG_DIR = os.getenv('LOG_DIR', 'logs')
LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', str(5 * 1024 * 1024)))
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '10'))

# Retry configuration
RETRY_ATTEMPTS = int(os.getenv('RETRY_ATTEMPTS', '3'))
RETRY_DELAY = float(os.getenv('RETRY_DELAY', '1.0'))

# Exchange fees configuration (total fee for round-trip trade)
EXCHANGE_FEES = {
    'polymarket': float(os.getenv('POLYMARKET_FEE', '0.002')),  # 0.2% total (0.1% per side)
    'sx': float(os.getenv('SX_FEE', '0.002')),  # 0.2% total (0.1% per side)
    'kalshi': float(os.getenv('KALSHI_FEE', '0.003')),  # 0.3% total (0.15% per side)
}
DEFAULT_FEE = float(os.getenv('DEFAULT_FEE', '0.002'))  # Default 0.2% total

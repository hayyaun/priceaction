"""
Configuration module for loading environment variables and settings.
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Configuration class for trading bot"""
    
    # Exchange Configuration
    EXCHANGE = os.getenv('EXCHANGE', 'binance')
    TESTNET = os.getenv('TESTNET', 'true').lower() == 'true'
    
    # API Keys
    API_KEY = os.getenv('API_KEY', '')
    API_SECRET = os.getenv('API_SECRET', '')
    
    # Trading Configuration
    SYMBOL = os.getenv('SYMBOL', 'BTC/USDT')  # Legacy single symbol support
    SYMBOLS = os.getenv('SYMBOLS', 'BTC/USDT,ETH/USDT,BNB/USDT,XRP/USDT,SOL/USDT,DOGE/USDT,ADA/USDT,DOT/USDT').split(',')
    TIMEFRAME = os.getenv('TIMEFRAME', '15m')
    
    # Risk Management
    RISK_PER_TRADE = float(os.getenv('RISK_PER_TRADE', '0.01'))
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '0.1'))
    STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', '0.02'))
    TAKE_PROFIT_PERCENT = float(os.getenv('TAKE_PROFIT_PERCENT', '0.04'))
    
    # Strategy Parameters
    EMA_FAST = int(os.getenv('EMA_FAST', '9'))
    EMA_SLOW = int(os.getenv('EMA_SLOW', '21'))
    RSI_PERIOD = int(os.getenv('RSI_PERIOD', '14'))
    RSI_OVERBOUGHT = int(os.getenv('RSI_OVERBOUGHT', '70'))
    RSI_OVERSOLD = int(os.getenv('RSI_OVERSOLD', '30'))
    
    # Execution
    DRY_RUN = os.getenv('DRY_RUN', 'true').lower() == 'true'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Telegram Notifications
    TELEGRAM_ENABLED = os.getenv('TELEGRAM_ENABLED', 'false').lower() == 'true'
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID', '')
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.API_KEY or not cls.API_SECRET:
            if not cls.DRY_RUN:
                raise ValueError("API_KEY and API_SECRET must be set for live trading")
        
        if cls.RISK_PER_TRADE <= 0 or cls.RISK_PER_TRADE > 0.05:
            raise ValueError("RISK_PER_TRADE should be between 0 and 0.05 (5%)")
        
        if cls.STOP_LOSS_PERCENT <= 0:
            raise ValueError("STOP_LOSS_PERCENT must be positive")
        
        if cls.TAKE_PROFIT_PERCENT <= 0:
            raise ValueError("TAKE_PROFIT_PERCENT must be positive")
        
        return True


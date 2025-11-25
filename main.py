"""
Main entry point for BTC/USDT trading bot
"""
import logging
import sys
from pathlib import Path

from config import Config
from strategy import PriceActionStrategy
from exchange import ExchangeConnector
from trading_service import TradingService
from telegram_bot import TelegramNotifier


def setup_logging():
    """Configure logging"""
    log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # File handler
    file_handler = logging.FileHandler(
        log_dir / 'trading_bot.log',
        mode='a'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger


def print_configuration():
    """Print current configuration"""
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 80)
    logger.info("BTC/USDT TRADING BOT CONFIGURATION")
    logger.info("=" * 80)
    logger.info(f"Exchange: {Config.EXCHANGE}")
    logger.info(f"Testnet: {Config.TESTNET}")
    logger.info(f"Symbol: {Config.SYMBOL}")
    logger.info(f"Timeframe: {Config.TIMEFRAME}")
    logger.info(f"Dry Run: {Config.DRY_RUN}")
    logger.info("-" * 80)
    logger.info("Risk Management:")
    logger.info(f"  Risk per trade: {Config.RISK_PER_TRADE * 100}%")
    logger.info(f"  Max position size: {Config.MAX_POSITION_SIZE * 100}%")
    logger.info(f"  Stop loss: {Config.STOP_LOSS_PERCENT * 100}%")
    logger.info(f"  Take profit: {Config.TAKE_PROFIT_PERCENT * 100}%")
    logger.info("-" * 80)
    logger.info("Strategy Parameters:")
    logger.info(f"  EMA Fast: {Config.EMA_FAST}")
    logger.info(f"  EMA Slow: {Config.EMA_SLOW}")
    logger.info(f"  RSI Period: {Config.RSI_PERIOD}")
    logger.info(f"  RSI Oversold: {Config.RSI_OVERSOLD}")
    logger.info(f"  RSI Overbought: {Config.RSI_OVERBOUGHT}")
    logger.info("=" * 80)


def main():
    """Main function"""
    # Setup logging
    logger = setup_logging()
    
    try:
        # Validate configuration
        Config.validate()
        
        # Print configuration
        print_configuration()
        
        # Warn if no API keys in dry run mode
        if Config.DRY_RUN and (not Config.API_KEY or not Config.API_SECRET):
            logger.warning("Running in DRY RUN mode without API keys")
            logger.warning("This will simulate trades without connecting to exchange")
        
        # Log trading mode
        if not Config.DRY_RUN and not Config.TESTNET:
            logger.warning("!" * 80)
            logger.warning("MAINNET LIVE TRADING - REAL MONEY AT RISK!")
            logger.warning("!" * 80)
        elif not Config.DRY_RUN and Config.TESTNET:
            logger.info("Testnet mode - trading with demo funds")
        
        # Initialize strategy
        strategy = PriceActionStrategy(
            ema_fast=Config.EMA_FAST,
            ema_slow=Config.EMA_SLOW,
            rsi_period=Config.RSI_PERIOD,
            rsi_overbought=Config.RSI_OVERBOUGHT,
            rsi_oversold=Config.RSI_OVERSOLD
        )
        
        # Initialize exchange connector
        exchange = ExchangeConnector(
            exchange_name=Config.EXCHANGE,
            api_key=Config.API_KEY,
            api_secret=Config.API_SECRET,
            testnet=Config.TESTNET,
            dry_run=Config.DRY_RUN
        )
        
        # Initialize Telegram notifier
        telegram = None
        if Config.TELEGRAM_ENABLED:
            telegram = TelegramNotifier(
                bot_token=Config.TELEGRAM_BOT_TOKEN,
                channel_id=Config.TELEGRAM_CHANNEL_ID,
                enabled=Config.TELEGRAM_ENABLED
            )
            logger.info("Telegram notifications enabled")
        
        # Initialize trading service
        trading_service = TradingService(
            exchange=exchange,
            strategy=strategy,
            config=Config,
            telegram=telegram
        )
        
        # Calculate check interval based on timeframe
        timeframe_to_seconds = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400
        }
        check_interval = timeframe_to_seconds.get(Config.TIMEFRAME, 900)
        
        # Start trading
        logger.info("Starting trading bot...")
        trading_service.run_forever(interval_seconds=check_interval)
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()


"""
Test script to verify exchange connection and fetch sample data
"""
import logging
from config import Config
from exchange import ExchangeConnector

# Setup simple logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Test exchange connection"""
    print("=" * 80)
    print("Testing Exchange Connection")
    print("=" * 80)
    print(f"Exchange: {Config.EXCHANGE}")
    print(f"Testnet: {Config.TESTNET}")
    print(f"Symbol: {Config.SYMBOL}")
    print(f"Dry Run: {Config.DRY_RUN}")
    print("=" * 80)
    print()
    
    try:
        # Initialize exchange
        logger.info("Initializing exchange connector...")
        exchange = ExchangeConnector(
            exchange_name=Config.EXCHANGE,
            api_key=Config.API_KEY,
            api_secret=Config.API_SECRET,
            testnet=Config.TESTNET,
            dry_run=Config.DRY_RUN
        )
        logger.info("✓ Exchange connector initialized successfully")
        print()
        
        # Test: Fetch current price
        logger.info(f"Fetching current price for {Config.SYMBOL}...")
        price = exchange.get_current_price(Config.SYMBOL)
        logger.info(f"✓ Current {Config.SYMBOL} price: ${price:,.2f}")
        print()
        
        # Test: Fetch OHLCV data
        logger.info(f"Fetching OHLCV data ({Config.TIMEFRAME})...")
        df = exchange.fetch_ohlcv(Config.SYMBOL, Config.TIMEFRAME, limit=10)
        logger.info(f"✓ Fetched {len(df)} candles")
        print()
        print("Latest 5 candles:")
        print(df[['open', 'high', 'low', 'close', 'volume']].tail())
        print()
        
        # Test: Check balance (only if not dry run)
        if not Config.DRY_RUN:
            logger.info("Checking account balance...")
            balance = exchange.get_balance('USDT')
            logger.info(f"✓ USDT Balance: ${balance:,.2f}")
        else:
            logger.info("⚠ Skipping balance check (dry run mode)")
        
        print()
        print("=" * 80)
        print("✓ All tests passed successfully!")
        print("=" * 80)
        print()
        print("You can now run the trading bot with: python3 main.py")
        print()
        
    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        print()
        print("=" * 80)
        print("✗ Connection test failed")
        print("=" * 80)
        print()
        print("Troubleshooting:")
        print("1. Check your .env file configuration")
        print("2. Verify API keys are correct")
        print("3. Ensure testnet/mainnet setting matches your keys")
        print("4. Check internet connection")
        print()


if __name__ == '__main__':
    main()


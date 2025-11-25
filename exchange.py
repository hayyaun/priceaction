"""
Exchange connector supporting both testnet and mainnet
"""
import ccxt
import pandas as pd
from typing import Optional, Dict, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ExchangeConnector:
    """
    Exchange connector with testnet/mainnet support
    Currently supports Binance with easy extension to other exchanges
    """
    
    def __init__(
        self,
        exchange_name: str,
        api_key: str,
        api_secret: str,
        testnet: bool = True,
        dry_run: bool = True
    ):
        """
        Initialize exchange connector
        
        Args:
            exchange_name: Exchange name (e.g., 'binance')
            api_key: API key
            api_secret: API secret
            testnet: Use testnet if True, mainnet if False
            dry_run: If True, don't execute real trades
        """
        self.exchange_name = exchange_name.lower()
        self.testnet = testnet
        self.dry_run = dry_run
        self.exchange = None
        
        # Initialize exchange
        self._init_exchange(api_key, api_secret)
        
        logger.info(
            f"Exchange initialized: {exchange_name}, "
            f"Testnet: {testnet}, Dry run: {dry_run}"
        )
    
    def _init_exchange(self, api_key: str, api_secret: str):
        """Initialize CCXT exchange instance"""
        # Skip actual exchange connection in dry run mode
        if self.dry_run:
            logger.info(f"Dry run mode - skipping exchange connection")
            self.exchange = None
            return
        
        try:
            # Get exchange class
            exchange_class = getattr(ccxt, self.exchange_name)
            
            # Configure exchange
            config = {
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'timeout': 30000,  # 30 second timeout
                'options': {
                    'defaultType': 'future',  # Use futures for both long/short
                }
            }
            
            self.exchange = exchange_class(config)
            
            # Enable testnet/demo mode if requested
            if self.testnet:
                if self.exchange_name == 'binance':
                    # Enable Binance demo/testnet mode (demo.binance.com)
                    self.exchange.set_sandbox_mode(True)
                    logger.info("Binance sandbox/demo mode enabled")
                # Add other exchanges' testnet configs here
            
            # Load markets
            self.exchange.load_markets()
            
            logger.info(f"Successfully connected to {self.exchange_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}")
            raise
    
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Timeframe (e.g., '15m', '1h')
            limit: Number of candles to fetch
            
        Returns:
            DataFrame with OHLCV data
        """
        if self.dry_run:
            # Generate simulated data for dry run
            import numpy as np
            from datetime import datetime, timedelta
            
            logger.debug(f"[DRY RUN] Generating simulated OHLCV data for {symbol}")
            
            # Generate realistic BTC price data around 95000
            base_price = 95000
            timestamps = []
            data = []
            
            now = datetime.now()
            for i in range(limit):
                ts = now - timedelta(minutes=15 * (limit - i))
                timestamps.append(ts)
                
                # Random walk price simulation
                change = np.random.normal(0, base_price * 0.002)  # 0.2% std dev
                price = base_price + change
                high = price * (1 + abs(np.random.normal(0, 0.001)))
                low = price * (1 - abs(np.random.normal(0, 0.001)))
                close = np.random.uniform(low, high)
                volume = np.random.uniform(100, 1000)
                
                data.append([ts, price, high, low, close, volume])
                base_price = close  # Walk from previous close
            
            df = pd.DataFrame(
                data,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df.set_index('timestamp', inplace=True)
            return df
        
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            logger.debug(f"Fetched {len(df)} candles for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV: {e}")
            raise
    
    def get_balance(self, currency: str = 'USDT') -> float:
        """
        Get account balance
        
        Args:
            currency: Currency to check (default: USDT)
            
        Returns:
            Available balance
        """
        if self.dry_run:
            # Simulated balance for dry run
            balance = 10000.0  # $10,000 USDT
            logger.info(f"[DRY RUN] Balance {currency}: {balance}")
            return balance
        
        try:
            balance = self.exchange.fetch_balance()
            available = balance.get(currency, {}).get('free', 0.0)
            
            logger.info(f"Balance {currency}: {available}")
            return float(available)
            
        except Exception as e:
            logger.error(f"Failed to fetch balance: {e}")
            raise
    
    def get_current_price(self, symbol: str) -> float:
        """Get current market price"""
        if self.dry_run:
            # Use last close price from simulated data
            df = self.fetch_ohlcv(symbol, '15m', limit=1)
            price = df['close'].iloc[-1]
            logger.debug(f"[DRY RUN] Current price {symbol}: {price}")
            return float(price)
        
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            price = ticker['last']
            logger.debug(f"Current price {symbol}: {price}")
            return float(price)
        except Exception as e:
            logger.error(f"Failed to fetch price: {e}")
            raise
    
    def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Create market order
        
        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Amount in base currency
            params: Additional parameters
            
        Returns:
            Order info or None if dry run
        """
        if self.dry_run:
            logger.info(
                f"[DRY RUN] Market {side} order: {amount} {symbol}"
            )
            return {
                'id': 'dry_run_' + datetime.now().strftime('%Y%m%d%H%M%S'),
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'type': 'market',
                'status': 'closed',
                'dry_run': True
            }
        
        try:
            logger.info(f"Creating market {side} order: {amount} {symbol}")
            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=amount,
                params=params or {}
            )
            logger.info(f"Order created: {order['id']}")
            return order
            
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            raise
    
    def create_stop_loss_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        stop_price: float,
        params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Create stop loss order
        
        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Amount in base currency
            stop_price: Stop loss trigger price
            params: Additional parameters
            
        Returns:
            Order info or None if dry run
        """
        if self.dry_run:
            logger.info(
                f"[DRY RUN] Stop loss {side} at {stop_price}: {amount} {symbol}"
            )
            return {
                'id': 'dry_run_sl_' + datetime.now().strftime('%Y%m%d%H%M%S'),
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'type': 'stop_market',
                'stopPrice': stop_price,
                'status': 'open',
                'dry_run': True
            }
        
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type='stop_market',
                side=side,
                amount=amount,
                params={
                    'stopPrice': stop_price,
                    **(params or {})
                }
            )
            logger.info(f"Stop loss order created: {order['id']} at {stop_price}")
            return order
            
        except Exception as e:
            logger.error(f"Failed to create stop loss: {e}")
            raise
    
    def create_take_profit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        limit_price: float,
        params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Create take profit order
        
        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Amount in base currency
            limit_price: Take profit price
            params: Additional parameters
            
        Returns:
            Order info or None if dry run
        """
        if self.dry_run:
            logger.info(
                f"[DRY RUN] Take profit {side} at {limit_price}: {amount} {symbol}"
            )
            return {
                'id': 'dry_run_tp_' + datetime.now().strftime('%Y%m%d%H%M%S'),
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'type': 'take_profit_market',
                'stopPrice': limit_price,
                'status': 'open',
                'dry_run': True
            }
        
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type='take_profit_market',
                side=side,
                amount=amount,
                params={
                    'stopPrice': limit_price,
                    **(params or {})
                }
            )
            logger.info(f"Take profit order created: {order['id']} at {limit_price}")
            return order
            
        except Exception as e:
            logger.error(f"Failed to create take profit: {e}")
            raise
    
    def get_open_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get open positions
        
        Args:
            symbol: Filter by symbol (optional)
            
        Returns:
            List of open positions
        """
        if self.dry_run:
            logger.debug("[DRY RUN] No real positions in dry run mode")
            return []
        
        try:
            positions = self.exchange.fetch_positions(symbol)
            # Filter out positions with zero contracts
            open_positions = [
                p for p in positions 
                if float(p.get('contracts', 0)) > 0
            ]
            logger.info(f"Open positions: {len(open_positions)}")
            return open_positions
            
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            raise
    
    def cancel_all_orders(self, symbol: str) -> bool:
        """Cancel all open orders for a symbol"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Cancel all orders for {symbol}")
            return True
        
        try:
            self.exchange.cancel_all_orders(symbol)
            logger.info(f"Cancelled all orders for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel orders: {e}")
            return False


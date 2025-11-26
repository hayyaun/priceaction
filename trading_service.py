"""
Main trading service orchestrating strategy and exchange operations
"""
import time
import logging
from typing import Optional, Dict
from datetime import datetime
import pandas as pd

from strategy import PriceActionStrategy, Signal
from exchange import ExchangeConnector
from config import Config
from telegram_bot import TelegramNotifier

logger = logging.getLogger(__name__)


class TradingService:
    """
    Trading service managing the complete trading lifecycle:
    - Data fetching
    - Signal generation
    - Position management
    - Risk management
    """
    
    def __init__(
        self,
        exchange: ExchangeConnector,
        strategy: PriceActionStrategy,
        config: Config,
        telegram: Optional[TelegramNotifier] = None
    ):
        """
        Initialize trading service
        
        Args:
            exchange: Exchange connector
            strategy: Trading strategy
            config: Configuration object
            telegram: Telegram notifier (optional)
        """
        self.exchange = exchange
        self.strategy = strategy
        self.config = config
        self.telegram = telegram
        
        # State management
        self.current_position: Optional[Dict] = None
        self.entry_price: Optional[float] = None
        self.position_size: Optional[float] = None
        self.stop_loss_order_id: Optional[str] = None
        self.take_profit_order_id: Optional[str] = None
        
        logger.info("Trading service initialized")
    
    def fetch_market_data(self) -> pd.DataFrame:
        """Fetch latest market data"""
        try:
            df = self.exchange.fetch_ohlcv(
                symbol=self.config.SYMBOL,
                timeframe=self.config.TIMEFRAME,
                limit=100  # Fetch enough data for indicators
            )
            logger.debug(f"Fetched market data: {len(df)} candles")
            return df
        except Exception as e:
            logger.error(f"Failed to fetch market data: {e}")
            raise
    
    def check_and_execute_signal(self):
        """Main trading logic: check signals and execute trades"""
        try:
            # Fetch market data
            df = self.fetch_market_data()
            
            # Determine current position status
            position_type = None
            if self.current_position:
                position_type = self.current_position.get('type')
            
            # Generate signal
            signal, info = self.strategy.generate_signal(df, position_type)
            
            logger.info(f"Signal: {signal.value}, Info: {info}")
            
            # Send Telegram notification for BUY/SELL signals only (skip HOLD to avoid spam)
            if self.telegram and signal != Signal.HOLD:
                self.telegram.notify_signal(signal.value, info)
            
            # Execute trades based on signal
            if signal == Signal.BUY and not self.current_position:
                self._execute_buy(info)
            elif signal == Signal.SELL and self.current_position:
                self._execute_sell(info)
            elif signal == Signal.HOLD:
                self._check_risk_management(info)
            
        except Exception as e:
            logger.error(f"Error in signal check: {e}")
    
    def _execute_buy(self, info: Dict):
        """Execute buy order and set up risk management"""
        try:
            # Get account balance
            balance = self.exchange.get_balance('USDT')
            current_price = info['price']
            
            if balance <= 0:
                logger.warning("Insufficient balance for trading")
                return
            
            # Calculate position size
            position_size = self.strategy.calculate_position_size(
                balance=balance,
                risk_per_trade=self.config.RISK_PER_TRADE,
                stop_loss_percent=self.config.STOP_LOSS_PERCENT,
                max_position_size=self.config.MAX_POSITION_SIZE,
                current_price=current_price
            )
            
            # Round to appropriate precision (exchange-specific)
            position_size = round(position_size, 6)
            
            if position_size <= 0:
                logger.warning("Position size too small")
                return
            
            # Execute market buy order
            logger.info(f"Executing BUY: {position_size} @ {current_price}")
            order = self.exchange.create_market_order(
                symbol=self.config.SYMBOL,
                side='buy',
                amount=position_size
            )
            
            if not order:
                logger.error("Failed to create buy order")
                return
            
            # Calculate stop loss and take profit
            stop_loss, take_profit = self.strategy.calculate_stop_loss_take_profit(
                entry_price=current_price,
                position_type='long',
                stop_loss_percent=self.config.STOP_LOSS_PERCENT,
                take_profit_percent=self.config.TAKE_PROFIT_PERCENT
            )
            
            # Place stop loss order
            sl_order = self.exchange.create_stop_loss_order(
                symbol=self.config.SYMBOL,
                side='sell',
                amount=position_size,
                stop_price=stop_loss
            )
            
            # Place take profit order
            tp_order = self.exchange.create_take_profit_order(
                symbol=self.config.SYMBOL,
                side='sell',
                amount=position_size,
                limit_price=take_profit
            )
            
            # Update position state
            self.current_position = {
                'type': 'long',
                'entry_price': current_price,
                'size': position_size,
                'entry_time': datetime.now(),
                'order_id': order.get('id'),
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }
            self.entry_price = current_price
            self.position_size = position_size
            self.stop_loss_order_id = sl_order.get('id') if sl_order else None
            self.take_profit_order_id = tp_order.get('id') if tp_order else None
            
            logger.info(
                f"Position opened: {position_size} @ {current_price}, "
                f"SL: {stop_loss}, TP: {take_profit}"
            )
            
            # Send Telegram notification
            if self.telegram:
                self.telegram.notify_trade('buy', current_price, position_size, 
                                          stop_loss, take_profit, symbol=self.config.SYMBOL)
            
        except Exception as e:
            logger.error(f"Failed to execute buy: {e}")
    
    def _execute_sell(self, info: Dict):
        """Execute sell order to close position"""
        try:
            if not self.current_position:
                logger.warning("No position to close")
                return
            
            position_size = self.current_position['size']
            entry_price = self.current_position['entry_price']
            current_price = info['price']
            
            # Calculate P&L
            pnl = (current_price - entry_price) * position_size
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            
            # Cancel existing stop loss and take profit orders
            if not self.config.DRY_RUN:
                self.exchange.cancel_all_orders(self.config.SYMBOL)
            
            # Execute market sell order
            logger.info(f"Executing SELL: {position_size} @ {current_price}")
            order = self.exchange.create_market_order(
                symbol=self.config.SYMBOL,
                side='sell',
                amount=position_size
            )
            
            if not order:
                logger.error("Failed to create sell order")
                return
            
            logger.info(
                f"Position closed: P&L = {pnl:.2f} USDT ({pnl_percent:.2f}%), "
                f"Entry: {entry_price}, Exit: {current_price}"
            )
            
            # Send Telegram notification
            if self.telegram:
                self.telegram.notify_position_closed(entry_price, current_price, 
                                                    position_size, pnl, pnl_percent, symbol=self.config.SYMBOL)
            
            # Clear position state
            self.current_position = None
            self.entry_price = None
            self.position_size = None
            self.stop_loss_order_id = None
            self.take_profit_order_id = None
            
        except Exception as e:
            logger.error(f"Failed to execute sell: {e}")
    
    def _check_risk_management(self, info: Dict):
        """Monitor and enforce risk management rules"""
        if not self.current_position:
            return
        
        try:
            current_price = info['price']
            entry_price = self.current_position['entry_price']
            stop_loss = self.current_position['stop_loss']
            take_profit = self.current_position['take_profit']
            
            # Calculate current P&L
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            
            # Check if stop loss or take profit hit
            if current_price <= stop_loss:
                logger.warning(f"Stop loss triggered at {current_price}")
                self._execute_sell(info)
            elif current_price >= take_profit:
                logger.info(f"Take profit triggered at {current_price}")
                self._execute_sell(info)
            else:
                logger.debug(
                    f"Position monitoring: P&L {pnl_percent:.2f}%, "
                    f"Price: {current_price}, SL: {stop_loss}, TP: {take_profit}"
                )
            
        except Exception as e:
            logger.error(f"Error in risk management: {e}")
    
    def get_status(self) -> Dict:
        """Get current trading service status"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'symbol': self.config.SYMBOL,
            'position': None,
            'balance': None
        }
        
        try:
            # Get balance
            status['balance'] = self.exchange.get_balance('USDT')
            
            # Get current price
            status['current_price'] = self.exchange.get_current_price(self.config.SYMBOL)
            
            # Position info
            if self.current_position:
                current_price = status['current_price']
                entry_price = self.current_position['entry_price']
                pnl_percent = ((current_price - entry_price) / entry_price) * 100
                
                status['position'] = {
                    'type': self.current_position['type'],
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'size': self.current_position['size'],
                    'pnl_percent': pnl_percent,
                    'stop_loss': self.current_position['stop_loss'],
                    'take_profit': self.current_position['take_profit'],
                    'entry_time': self.current_position['entry_time'].isoformat()
                }
            
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
        
        return status
    
    def run_forever(self, interval_seconds: int = 60):
        """
        Run trading service continuously
        
        Args:
            interval_seconds: Check interval in seconds
        """
        logger.info(f"Starting trading service (interval: {interval_seconds}s)")
        
        while True:
            try:
                logger.info("=" * 80)
                logger.info(f"Trading cycle at {datetime.now()}")
                
                # Check and execute signals
                self.check_and_execute_signal()
                
                # Print status
                status = self.get_status()
                logger.info(f"Status: {status}")
                
                # Sleep until next cycle
                logger.info(f"Sleeping for {interval_seconds} seconds...")
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Shutting down trading service...")
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                time.sleep(interval_seconds)


"""
Multi-pair trading service for handling multiple symbols simultaneously
"""
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

from strategy import PriceActionStrategy, Signal
from exchange import ExchangeConnector
from config import Config
from telegram_bot import TelegramNotifier

logger = logging.getLogger(__name__)


class MultiPairTradingService:
    """
    Trading service managing multiple trading pairs simultaneously
    Each pair has its own position tracking and strategy execution
    """
    
    def __init__(
        self,
        exchange: ExchangeConnector,
        strategy_params: Dict,
        config: Config,
        symbols: List[str],
        telegram: Optional[TelegramNotifier] = None
    ):
        """
        Initialize multi-pair trading service
        
        Args:
            exchange: Exchange connector
            strategy_params: Strategy parameters dict
            config: Configuration object
            symbols: List of trading symbols
            telegram: Telegram notifier (optional)
        """
        self.exchange = exchange
        self.config = config
        self.telegram = telegram
        self.symbols = symbols
        
        # Create strategy instance for each symbol
        self.strategies = {}
        for symbol in symbols:
            self.strategies[symbol] = PriceActionStrategy(**strategy_params)
        
        # Track positions for each symbol
        self.positions: Dict[str, Optional[Dict]] = {symbol: None for symbol in symbols}
        self.stop_loss_orders: Dict[str, Optional[str]] = {symbol: None for symbol in symbols}
        self.take_profit_orders: Dict[str, Optional[str]] = {symbol: None for symbol in symbols}
        
        logger.info(f"Multi-pair trading service initialized for {len(symbols)} pairs: {', '.join(symbols)}")
    
    def fetch_market_data(self, symbol: str) -> pd.DataFrame:
        """Fetch latest market data for a symbol"""
        try:
            df = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=self.config.TIMEFRAME,
                limit=100
            )
            logger.debug(f"[{symbol}] Fetched market data: {len(df)} candles")
            return df
        except Exception as e:
            logger.error(f"[{symbol}] Failed to fetch market data: {e}")
            raise
    
    def check_and_execute_signal_for_pair(self, symbol: str):
        """Check signals and execute trades for a specific pair"""
        try:
            # Fetch market data
            df = self.fetch_market_data(symbol)
            
            # Determine current position status
            position_type = None
            if self.positions[symbol]:
                position_type = self.positions[symbol].get('type')
            
            # Generate signal
            signal, info = self.strategies[symbol].generate_signal(df, position_type)
            
            logger.info(f"[{symbol}] Signal: {signal.value}, Price: {info['price']:.2f}")
            
            # Send Telegram notification for BUY/SELL signals only (skip HOLD to avoid spam)
            if self.telegram and signal != Signal.HOLD:
                # Add symbol to info for telegram message
                info['symbol'] = symbol
                self.telegram.notify_signal(signal.value, info)
            
            # Execute trades based on signal
            if signal == Signal.BUY and not self.positions[symbol]:
                self._execute_buy(symbol, info)
            elif signal == Signal.SELL and self.positions[symbol]:
                self._execute_sell(symbol, info)
            elif signal == Signal.HOLD:
                self._check_risk_management(symbol, info)
            
        except Exception as e:
            logger.error(f"[{symbol}] Error in signal check: {e}")
    
    def _execute_buy(self, symbol: str, info: Dict):
        """Execute buy order for a specific pair"""
        try:
            # Get account balance
            balance = self.exchange.get_balance('USDT')
            current_price = info['price']
            
            if balance <= 0:
                logger.warning(f"[{symbol}] Insufficient balance for trading")
                return
            
            # Calculate available balance (divide by number of active positions + this new one)
            active_positions = sum(1 for pos in self.positions.values() if pos is not None)
            available_slots = len(self.symbols)
            balance_per_pair = balance / available_slots
            
            # Calculate position size
            position_size = self.strategies[symbol].calculate_position_size(
                balance=balance_per_pair,
                risk_per_trade=self.config.RISK_PER_TRADE,
                stop_loss_percent=self.config.STOP_LOSS_PERCENT,
                max_position_size=self.config.MAX_POSITION_SIZE,
                current_price=current_price
            )
            
            # Round to appropriate precision
            position_size = round(position_size, 6)
            
            if position_size <= 0:
                logger.warning(f"[{symbol}] Position size too small")
                return
            
            # Execute market buy order
            logger.info(f"[{symbol}] Executing BUY: {position_size} @ {current_price}")
            order = self.exchange.create_market_order(
                symbol=symbol,
                side='buy',
                amount=position_size
            )
            
            if not order:
                logger.error(f"[{symbol}] Failed to create buy order")
                return
            
            # Calculate stop loss and take profit
            stop_loss, take_profit = self.strategies[symbol].calculate_stop_loss_take_profit(
                entry_price=current_price,
                position_type='long',
                stop_loss_percent=self.config.STOP_LOSS_PERCENT,
                take_profit_percent=self.config.TAKE_PROFIT_PERCENT
            )
            
            # Place stop loss order
            sl_order = self.exchange.create_stop_loss_order(
                symbol=symbol,
                side='sell',
                amount=position_size,
                stop_price=stop_loss
            )
            
            # Place take profit order
            tp_order = self.exchange.create_take_profit_order(
                symbol=symbol,
                side='sell',
                amount=position_size,
                limit_price=take_profit
            )
            
            # Update position state
            self.positions[symbol] = {
                'type': 'long',
                'entry_price': current_price,
                'size': position_size,
                'entry_time': datetime.now(),
                'order_id': order.get('id'),
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }
            self.stop_loss_orders[symbol] = sl_order.get('id') if sl_order else None
            self.take_profit_orders[symbol] = tp_order.get('id') if tp_order else None
            
            logger.info(
                f"[{symbol}] Position opened: {position_size} @ {current_price}, "
                f"SL: {stop_loss}, TP: {take_profit}"
            )
            
            # Send Telegram notification with symbol
            if self.telegram:
                info['symbol'] = symbol
                self.telegram.notify_trade('buy', current_price, position_size, 
                                          stop_loss, take_profit, symbol=symbol)
            
        except Exception as e:
            logger.error(f"[{symbol}] Failed to execute buy: {e}")
    
    def _execute_sell(self, symbol: str, info: Dict):
        """Execute sell order for a specific pair"""
        try:
            if not self.positions[symbol]:
                logger.warning(f"[{symbol}] No position to close")
                return
            
            position_size = self.positions[symbol]['size']
            entry_price = self.positions[symbol]['entry_price']
            current_price = info['price']
            
            # Calculate P&L
            pnl = (current_price - entry_price) * position_size
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            
            # Cancel existing stop loss and take profit orders
            if not self.config.DRY_RUN:
                self.exchange.cancel_all_orders(symbol)
            
            # Execute market sell order
            logger.info(f"[{symbol}] Executing SELL: {position_size} @ {current_price}")
            order = self.exchange.create_market_order(
                symbol=symbol,
                side='sell',
                amount=position_size
            )
            
            if not order:
                logger.error(f"[{symbol}] Failed to create sell order")
                return
            
            logger.info(
                f"[{symbol}] Position closed: P&L = {pnl:.2f} USDT ({pnl_percent:.2f}%), "
                f"Entry: {entry_price}, Exit: {current_price}"
            )
            
            # Send Telegram notification
            if self.telegram:
                self.telegram.notify_position_closed(entry_price, current_price, 
                                                    position_size, pnl, pnl_percent, symbol=symbol)
            
            # Clear position state
            self.positions[symbol] = None
            self.stop_loss_orders[symbol] = None
            self.take_profit_orders[symbol] = None
            
        except Exception as e:
            logger.error(f"[{symbol}] Failed to execute sell: {e}")
    
    def _check_risk_management(self, symbol: str, info: Dict):
        """Monitor and enforce risk management rules for a specific pair"""
        if not self.positions[symbol]:
            return
        
        try:
            current_price = info['price']
            entry_price = self.positions[symbol]['entry_price']
            stop_loss = self.positions[symbol]['stop_loss']
            take_profit = self.positions[symbol]['take_profit']
            
            # Calculate current P&L
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            
            # Check if stop loss or take profit hit
            if current_price <= stop_loss:
                logger.warning(f"[{symbol}] Stop loss triggered at {current_price}")
                self._execute_sell(symbol, info)
            elif current_price >= take_profit:
                logger.info(f"[{symbol}] Take profit triggered at {current_price}")
                self._execute_sell(symbol, info)
            else:
                logger.debug(
                    f"[{symbol}] Position monitoring: P&L {pnl_percent:.2f}%, "
                    f"Price: {current_price}, SL: {stop_loss}, TP: {take_profit}"
                )
            
        except Exception as e:
            logger.error(f"[{symbol}] Error in risk management: {e}")
    
    def check_all_pairs(self):
        """Check signals for all pairs (can be run in parallel)"""
        logger.info("=" * 80)
        logger.info(f"Checking all {len(self.symbols)} pairs at {datetime.now()}")
        
        # Process all pairs in parallel for efficiency
        with ThreadPoolExecutor(max_workers=min(len(self.symbols), 8)) as executor:
            futures = {
                executor.submit(self.check_and_execute_signal_for_pair, symbol): symbol 
                for symbol in self.symbols
            }
            
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"[{symbol}] Error processing pair: {e}")
    
    def get_status(self) -> Dict:
        """Get current trading service status for all pairs"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'total_pairs': len(self.symbols),
            'balance': None,
            'pairs': {}
        }
        
        try:
            # Get balance
            status['balance'] = self.exchange.get_balance('USDT')
            
            # Get status for each pair
            for symbol in self.symbols:
                try:
                    current_price = self.exchange.get_current_price(symbol)
                    
                    pair_status = {
                        'symbol': symbol,
                        'current_price': current_price,
                        'position': None
                    }
                    
                    # Position info
                    if self.positions[symbol]:
                        entry_price = self.positions[symbol]['entry_price']
                        pnl_percent = ((current_price - entry_price) / entry_price) * 100
                        
                        pair_status['position'] = {
                            'type': self.positions[symbol]['type'],
                            'entry_price': entry_price,
                            'size': self.positions[symbol]['size'],
                            'pnl_percent': pnl_percent,
                            'stop_loss': self.positions[symbol]['stop_loss'],
                            'take_profit': self.positions[symbol]['take_profit'],
                            'entry_time': self.positions[symbol]['entry_time'].isoformat()
                        }
                    
                    status['pairs'][symbol] = pair_status
                    
                except Exception as e:
                    logger.error(f"[{symbol}] Failed to get status: {e}")
                    status['pairs'][symbol] = {'error': str(e)}
            
        except Exception as e:
            logger.error(f"Failed to get overall status: {e}")
        
        return status
    
    def run_forever(self, interval_seconds: int = 60):
        """
        Run trading service continuously for all pairs
        
        Args:
            interval_seconds: Check interval in seconds
        """
        logger.info(f"Starting multi-pair trading service (interval: {interval_seconds}s)")
        logger.info(f"Trading pairs: {', '.join(self.symbols)}")
        
        while True:
            try:
                # Check and execute signals for all pairs
                self.check_all_pairs()
                
                # Print status
                status = self.get_status()
                active_positions = sum(1 for pair in status['pairs'].values() 
                                      if pair.get('position') is not None)
                logger.info(f"Status: Balance: {status['balance']:.2f} USDT, "
                           f"Active positions: {active_positions}/{len(self.symbols)}")
                
                # Sleep until next cycle
                logger.info(f"Sleeping for {interval_seconds} seconds...")
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Shutting down multi-pair trading service...")
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                time.sleep(interval_seconds)


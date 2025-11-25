"""
Safe Price-Action Trading Strategy
Uses EMA crossover + RSI with strict risk management
"""
import pandas as pd
import numpy as np
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from typing import Optional, Dict, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Signal(Enum):
    """Trading signals"""
    BUY = 'BUY'
    SELL = 'SELL'
    HOLD = 'HOLD'


class PriceActionStrategy:
    """
    Safe Price-Action Strategy combining:
    - EMA Crossover for trend detection
    - RSI for overbought/oversold conditions
    - Confirmation requirements to avoid false signals
    """
    
    def __init__(
        self,
        ema_fast: int = 9,
        ema_slow: int = 21,
        rsi_period: int = 14,
        rsi_overbought: int = 70,
        rsi_oversold: int = 30
    ):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        
        logger.info(
            f"Strategy initialized: EMA({ema_fast}/{ema_slow}), "
            f"RSI({rsi_period}, {rsi_oversold}/{rsi_overbought})"
        )
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with indicators added
        """
        df = df.copy()
        
        # Calculate EMAs
        ema_fast = EMAIndicator(close=df['close'], window=self.ema_fast)
        ema_slow = EMAIndicator(close=df['close'], window=self.ema_slow)
        df['ema_fast'] = ema_fast.ema_indicator()
        df['ema_slow'] = ema_slow.ema_indicator()
        
        # Calculate RSI
        rsi = RSIIndicator(close=df['close'], window=self.rsi_period)
        df['rsi'] = rsi.rsi()
        
        # Calculate trend strength (distance between EMAs)
        df['ema_diff'] = ((df['ema_fast'] - df['ema_slow']) / df['ema_slow']) * 100
        
        # Identify crossovers
        df['ema_cross_up'] = (
            (df['ema_fast'] > df['ema_slow']) & 
            (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1))
        )
        df['ema_cross_down'] = (
            (df['ema_fast'] < df['ema_slow']) & 
            (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1))
        )
        
        return df
    
    def generate_signal(
        self, 
        df: pd.DataFrame, 
        position: Optional[str] = None
    ) -> Tuple[Signal, Dict]:
        """
        Generate trading signal with confirmation
        
        Args:
            df: DataFrame with OHLCV data and indicators
            position: Current position ('long', 'short', or None)
            
        Returns:
            Tuple of (Signal, additional_info)
        """
        if len(df) < max(self.ema_slow, self.rsi_period) + 1:
            logger.warning("Insufficient data for signal generation")
            return Signal.HOLD, {'reason': 'insufficient_data'}
        
        # Calculate indicators
        df = self.calculate_indicators(df)
        
        # Get latest values
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        info = {
            'price': current['close'],
            'ema_fast': current['ema_fast'],
            'ema_slow': current['ema_slow'],
            'rsi': current['rsi'],
            'ema_diff': current['ema_diff']
        }
        
        # Exit signals (higher priority for risk management)
        if position == 'long':
            # Exit long if bearish crossover or RSI overbought
            if current['ema_cross_down'] or current['rsi'] > self.rsi_overbought:
                info['reason'] = 'exit_long_signal'
                logger.info(f"Exit LONG signal: {info}")
                return Signal.SELL, info
        
        # Entry signals (with strict confirmation)
        if position is None:
            # Buy signal: Bullish EMA crossover + RSI not overbought + trend strength
            if (current['ema_cross_up'] and 
                current['rsi'] < self.rsi_overbought and
                current['rsi'] > self.rsi_oversold and
                abs(current['ema_diff']) > 0.1):  # Minimum trend strength
                
                # Additional confirmation: price above both EMAs
                if current['close'] > current['ema_fast'] > current['ema_slow']:
                    info['reason'] = 'bullish_crossover_confirmed'
                    logger.info(f"BUY signal: {info}")
                    return Signal.BUY, info
        
        # Default: HOLD
        info['reason'] = 'no_signal'
        return Signal.HOLD, info
    
    def calculate_position_size(
        self,
        balance: float,
        risk_per_trade: float,
        stop_loss_percent: float,
        max_position_size: float,
        current_price: float
    ) -> float:
        """
        Calculate safe position size based on risk management
        
        Args:
            balance: Account balance in quote currency (USDT)
            risk_per_trade: Fraction of balance to risk (e.g., 0.01 = 1%)
            stop_loss_percent: Stop loss as fraction (e.g., 0.02 = 2%)
            max_position_size: Maximum position as fraction of balance
            current_price: Current asset price
            
        Returns:
            Position size in base currency (BTC)
        """
        # Calculate risk amount
        risk_amount = balance * risk_per_trade
        
        # Calculate position size based on stop loss
        position_value = risk_amount / stop_loss_percent
        
        # Apply maximum position size limit
        max_position_value = balance * max_position_size
        position_value = min(position_value, max_position_value)
        
        # Convert to base currency quantity
        quantity = position_value / current_price
        
        logger.info(
            f"Position sizing: Balance={balance}, Risk={risk_amount}, "
            f"Position Value={position_value}, Quantity={quantity}"
        )
        
        return quantity
    
    def calculate_stop_loss_take_profit(
        self,
        entry_price: float,
        position_type: str,
        stop_loss_percent: float,
        take_profit_percent: float
    ) -> Tuple[float, float]:
        """
        Calculate stop loss and take profit levels
        
        Args:
            entry_price: Entry price
            position_type: 'long' or 'short'
            stop_loss_percent: Stop loss percentage
            take_profit_percent: Take profit percentage
            
        Returns:
            Tuple of (stop_loss_price, take_profit_price)
        """
        if position_type == 'long':
            stop_loss = entry_price * (1 - stop_loss_percent)
            take_profit = entry_price * (1 + take_profit_percent)
        else:  # short
            stop_loss = entry_price * (1 + stop_loss_percent)
            take_profit = entry_price * (1 - take_profit_percent)
        
        logger.info(
            f"SL/TP calculated: Entry={entry_price}, "
            f"SL={stop_loss}, TP={take_profit}"
        )
        
        return stop_loss, take_profit


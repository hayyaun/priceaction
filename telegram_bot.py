"""
Telegram notification bot for trading signals
"""
import logging
import asyncio
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send trading signals to Telegram channel"""
    
    def __init__(self, bot_token: str, channel_id: str, enabled: bool = True):
        """
        Initialize Telegram notifier
        
        Args:
            bot_token: Telegram bot token from @BotFather
            channel_id: Channel ID (e.g., @your_channel or -1001234567890)
            enabled: Enable/disable notifications
        """
        self.enabled = enabled and bot_token and channel_id
        
        if self.enabled:
            self.bot = Bot(token=bot_token)
            self.channel_id = channel_id
            logger.info(f"Telegram notifier initialized for channel: {channel_id}")
        else:
            self.bot = None
            logger.info("Telegram notifier disabled")
    
    def send_message(self, message: str):
        """
        Send message to Telegram channel (sync wrapper)
        
        Args:
            message: Message text
        """
        if not self.enabled:
            return
        
        try:
            asyncio.run(self._send_message_async(message))
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
    
    async def _send_message_async(self, message: str):
        """Send message asynchronously"""
        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode='HTML'
            )
            logger.debug("Telegram message sent successfully")
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
    
    def notify_signal(self, signal: str, info: dict):
        """
        Send trading signal notification
        
        Args:
            signal: Signal type (BUY/SELL/HOLD)
            info: Signal information
        """
        if not self.enabled:
            return
        
        # Format message
        if signal == 'BUY':
            emoji = "🟢"
            title = "BUY SIGNAL"
        elif signal == 'SELL':
            emoji = "🔴"
            title = "SELL SIGNAL"
        elif signal == 'HOLD':
            emoji = "⏸️"
            title = "HOLD"
        else:
            return
        
        message = f"""
{emoji} <b>{title}</b>

💰 Price: ${info.get('price', 0):,.2f}
📊 EMA Fast: ${info.get('ema_fast', 0):,.2f}
📊 EMA Slow: ${info.get('ema_slow', 0):,.2f}
📈 RSI: {info.get('rsi', 0):.1f}
📐 EMA Diff: {info.get('ema_diff', 0):.2f}%

💡 Reason: {info.get('reason', 'N/A')}
"""
        
        self.send_message(message.strip())
    
    def notify_trade(self, action: str, price: float, size: float, 
                     stop_loss: Optional[float] = None, 
                     take_profit: Optional[float] = None):
        """
        Send trade execution notification
        
        Args:
            action: Trade action (buy/sell)
            price: Execution price
            size: Position size
            stop_loss: Stop loss price
            take_profit: Take profit price
        """
        if not self.enabled:
            return
        
        if action.lower() == 'buy':
            emoji = "✅"
            title = "TRADE EXECUTED - BUY"
        else:
            emoji = "❌"
            title = "TRADE EXECUTED - SELL"
        
        message = f"""
{emoji} <b>{title}</b>

💰 Price: ${price:,.2f}
📦 Size: {size:.6f} BTC
💵 Value: ${price * size:,.2f}
"""
        
        if stop_loss:
            message += f"\n🛑 Stop Loss: ${stop_loss:,.2f} ({((stop_loss/price - 1) * 100):.2f}%)"
        
        if take_profit:
            message += f"\n🎯 Take Profit: ${take_profit:,.2f} ({((take_profit/price - 1) * 100):.2f}%)"
        
        self.send_message(message.strip())
    
    def notify_position_closed(self, entry_price: float, exit_price: float, 
                               size: float, pnl: float, pnl_percent: float):
        """
        Send position closed notification
        
        Args:
            entry_price: Entry price
            exit_price: Exit price
            size: Position size
            pnl: Profit/Loss in USDT
            pnl_percent: P&L percentage
        """
        if not self.enabled:
            return
        
        if pnl >= 0:
            emoji = "💰"
            status = "PROFIT"
        else:
            emoji = "📉"
            status = "LOSS"
        
        message = f"""
{emoji} <b>POSITION CLOSED - {status}</b>

📥 Entry: ${entry_price:,.2f}
📤 Exit: ${exit_price:,.2f}
📦 Size: {size:.6f} BTC

💵 P&L: ${pnl:,.2f} ({pnl_percent:+.2f}%)
"""
        
        self.send_message(message.strip())
    
    def notify_error(self, error_msg: str):
        """Send error notification"""
        if not self.enabled:
            return
        
        message = f"""
⚠️ <b>ERROR</b>

{error_msg}
"""
        
        self.send_message(message.strip())
    
    def notify_status(self, balance: float, position: Optional[dict], 
                      current_price: float):
        """
        Send status update
        
        Args:
            balance: Account balance
            position: Current position info
            current_price: Current BTC price
        """
        if not self.enabled:
            return
        
        message = f"""
📊 <b>STATUS UPDATE</b>

💰 Balance: ${balance:,.2f}
💵 BTC Price: ${current_price:,.2f}
"""
        
        if position:
            pnl_percent = position.get('pnl_percent', 0)
            emoji = "📈" if pnl_percent >= 0 else "📉"
            
            message += f"""
{emoji} Position: OPEN
📥 Entry: ${position.get('entry_price', 0):,.2f}
📦 Size: {position.get('size', 0):.6f} BTC
💵 P&L: {pnl_percent:+.2f}%
🛑 Stop Loss: ${position.get('stop_loss', 0):,.2f}
🎯 Take Profit: ${position.get('take_profit', 0):,.2f}
"""
        else:
            message += "\n⏳ Position: NONE"
        
        self.send_message(message.strip())


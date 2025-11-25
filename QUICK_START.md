# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Install Dependencies
```bash
chmod +x setup.sh
./setup.sh
```

Or manually:
```bash
pip install -r requirements.txt
cp config.example.env .env
```

### Step 2: Configure Your Bot

Edit `.env` file:

**For First Test (No API Keys Needed):**
```env
DRY_RUN=true
TESTNET=true
# Leave API keys empty for initial test
```

**For Testnet Trading:**
```env
DRY_RUN=false
TESTNET=true
API_KEY=your_testnet_api_key_here
API_SECRET=your_testnet_secret_here
```

**For Live Trading (After Testing):**
```env
DRY_RUN=false
TESTNET=false
API_KEY=your_mainnet_api_key_here
API_SECRET=your_mainnet_secret_here
```

### Step 3: Test Connection (Optional)
```bash
python3 test_connection.py
```

This verifies your configuration and exchange connection.

### Step 4: Run the Bot
```bash
python3 main.py
```

## 📋 Configuration Options

### Risk Settings (IMPORTANT!)
```env
RISK_PER_TRADE=0.01      # Risk 1% per trade (RECOMMENDED)
MAX_POSITION_SIZE=0.1    # Max 10% of account
STOP_LOSS_PERCENT=0.02   # 2% stop loss
TAKE_PROFIT_PERCENT=0.04 # 4% take profit
```

### Trading Timeframes
```env
TIMEFRAME=15m  # Options: 1m, 5m, 15m, 1h, 4h, 1d
```
- `15m`: Recommended for active trading
- `1h`: More stable, fewer trades
- `4h` or `1d`: Very conservative

### Strategy Parameters
```env
EMA_FAST=9      # Fast EMA (default: 9)
EMA_SLOW=21     # Slow EMA (default: 21)
RSI_PERIOD=14   # RSI period (default: 14)
```

## 🔐 Getting API Keys

### Binance Testnet (Free Test Funds)
1. Go to: https://testnet.binancefuture.com/
2. Register with email
3. Go to API Key management
4. Create new API key
5. Copy both API Key and Secret to `.env`
6. Request test USDT from faucet

### Binance Mainnet (Real Money)
1. Go to: https://www.binance.com/
2. Complete registration and KYC
3. Enable 2FA (required!)
4. Go to Account → API Management
5. Create API key with these settings:
   - ✓ Enable Reading
   - ✓ Enable Futures
   - ✗ Disable Spot & Margin Trading
   - ✗ Disable Withdrawals (IMPORTANT!)
6. Whitelist your IP address
7. Copy keys to `.env`

## 🎯 Trading Strategy Explained

The bot uses a **conservative price-action strategy**:

1. **Entry Signal**: 
   - Fast EMA crosses above Slow EMA (bullish trend)
   - RSI between 30-70 (not overbought/oversold)
   - Price above both EMAs (confirmation)
   - Minimum trend strength met

2. **Exit Signal**:
   - Fast EMA crosses below Slow EMA
   - RSI reaches overbought (>70)
   - Stop loss hit (2% below entry)
   - Take profit hit (4% above entry)

3. **Risk Management**:
   - Position sized based on account risk (1%)
   - Automatic stop-loss on every trade
   - Automatic take-profit at 2:1 reward/risk
   - Maximum position limit (10% of account)

## 📊 What to Expect

### Trading Frequency
- **15m timeframe**: 1-5 trades per day
- **1h timeframe**: 1-3 trades per day
- **4h timeframe**: 1-5 trades per week

### Risk/Reward
- **Stop Loss**: 2% per trade
- **Take Profit**: 4% per trade
- **Risk/Reward Ratio**: 1:2

### Win Rate Target
- Strategy aims for 40-50% win rate
- With 1:2 R/R, this is profitable long-term

## ⚠️ Safety Checklist

Before running with real money:

- [ ] Tested in dry run mode
- [ ] Tested on testnet for at least 1 week
- [ ] Understand the strategy completely
- [ ] Set risk per trade to 1% or less
- [ ] API keys have NO withdrawal permission
- [ ] API keys are IP whitelisted
- [ ] 2FA enabled on exchange account
- [ ] Monitoring plan in place
- [ ] Know how to stop the bot (Ctrl+C)

## 🔍 Monitoring Your Bot

### Check Logs
```bash
# Follow live logs
tail -f logs/trading_bot.log

# View recent activity
tail -100 logs/trading_bot.log
```

### What to Monitor
- Signal generation (are signals being found?)
- Trade execution (successful orders?)
- Position management (stop loss/take profit working?)
- Account balance changes
- Error messages

## 🛑 How to Stop the Bot

Press `Ctrl+C` in the terminal where the bot is running.

The bot will:
1. Complete current operations
2. Log shutdown message
3. Exit gracefully

**Note**: Open positions will remain open after stopping the bot!

## 📈 Performance Tips

1. **Start Small**: Begin with minimum risk settings
2. **Test First**: Always test on testnet
3. **Monitor Daily**: Check logs and performance
4. **Adjust Gradually**: Make small parameter changes
5. **Be Patient**: Don't expect profits immediately
6. **Track Results**: Keep a trading journal

## ❓ Troubleshooting

### Bot doesn't trade
- Check if market meets entry conditions (see logs)
- Verify sufficient account balance
- Ensure `DRY_RUN=false` for real trades
- Check timeframe (longer = fewer trades)

### "API Error" messages
- Verify API keys are correct
- Check testnet/mainnet setting matches keys
- Ensure API has futures trading permission
- Check IP whitelist

### "Insufficient balance"
- Add funds to futures wallet
- For testnet: request test funds
- Check minimum order size requirements

## 📚 Learn More

- Full documentation: `README.md`
- Test connection: `python3 test_connection.py`
- View strategy code: `strategy.py`
- Exchange connector: `exchange.py`

## 🆘 Need Help?

1. Read error messages in logs
2. Check configuration in `.env`
3. Verify API keys and permissions
4. Test in dry run mode first
5. Review README.md for detailed info

## 💡 Pro Tips

- **Backtest** parameters on historical data before using
- **Start conservative** with 0.5% risk per trade
- **Use 15m or 1h** timeframe for best results
- **Monitor for 1 week** before increasing position sizes
- **Keep a journal** of trades and observations
- **Don't over-optimize** - simple strategies work best

---

**Ready to trade? Start with dry run mode!**

```bash
python3 main.py
```

Good luck and trade safely! 🚀📈


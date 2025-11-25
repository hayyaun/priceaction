# BTC/USDT Trading Bot

Automated crypto trading with EMA + RSI strategy.

## Quick Start

```bash
cp config.example.env .env
nano .env  # Add your API keys
make up
```

Done.

## Commands

```bash
make up       # Start
make down     # Stop
make restart  # Restart
make logs     # View logs
make run      # Deploy (git pull + restart)
```

## Configuration (.env)

```env
# Get keys from demo.binance.com
TESTNET=true
DRY_RUN=false
API_KEY=your_key
API_SECRET=your_secret

# Optional: Telegram notifications
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=get_from_@BotFather
TELEGRAM_CHANNEL_ID=@your_channel
```

## Strategy

- **Entry**: EMA(9) crosses above EMA(21) + RSI 30-70
- **Exit**: Reverse cross, RSI>70, or SL/TP
- **Risk**: 1% per trade, 2% SL, 4% TP
- **Frequency**: Checks every 15 minutes

## API Keys

**Demo**: https://demo.binance.com (Recommended first)
**Live**: https://www.binance.com (After testing)

Enable Futures, disable Withdrawals.

## Telegram

1. Message `@BotFather` → `/newbot`
2. Create channel, add bot as admin
3. Add token to `.env`

## Files

- `main.py` - Entry point
- `strategy.py` - EMA + RSI logic
- `exchange.py` - Binance connector
- `trading_service.py` - Trading execution
- `telegram_bot.py` - Notifications
- `Dockerfile` / `docker-compose.yml` - Docker setup

## Without Docker

```bash
pip3 install -r requirements.txt
cp config.example.env .env
nano .env
python3 main.py
```

## Safety

- Test on demo first
- Start small
- Monitor daily
- Never enable withdrawal permissions

**Trade safely!**


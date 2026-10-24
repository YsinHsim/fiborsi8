# FiboRSI8 Bot

A small Telegram alert bot for the FiboRSI8 setup: Fibonacci retracement + RSI(8) with a trend filter. It watches crypto pairs on Binance public market data and messages you when a closed candle matches the rules.

Alerts only. It never places trades. Signals are not financial advice, so check the chart before acting.

Built to run 24/7 on an old Android phone with Termux. Python standard library only, no `pip install` needed.

## Strategy rules

Checked on every **closed** candle, for every symbol and timeframe in `config.json`:

| | LONG | SHORT |
|---|---|---|
| Trend | close above SMA(50) | close below SMA(50) |
| Fibonacci | price touched the 61.8% pullback level of the last 50 candles' swing, within the last 3 candles | price touched the 61.8% rally level, within the last 3 candles |
| RSI(8) | crosses back above 30 | crosses back below 70 |
| Reference stop / target | swing low / swing high | swing high / swing low |

Each signal is sent once per candle. All numbers are configurable in `config.json` under `strategy`.

## Setup on the phone

### 1. Create the Telegram bot

1. In Telegram, message `@BotFather`, send `/newbot`, and copy the **token**.
2. Send any message to your new bot.
3. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and copy `"chat":{"id": ...}`. That number is your **chat_id**.

### 2. Install the apps

Install **Termux** and **Termux:Boot** from [F-Droid](https://f-droid.org/packages/com.termux/) or the [Termux GitHub releases](https://github.com/termux/termux-app/releases). Do not use the Play Store version of Termux, it is outdated.

### 3. Install the bot

In Termux:

```bash
pkg install -y git
git clone https://github.com/YsinHsim/fiborsi8.git
cd fiborsi8
./install.sh
```

The installer asks for your token and chat_id, sends a test message, sets up auto-start on boot, and starts the bot.

### 4. Stop Android from killing it

- Open the **Termux:Boot** app once.
- Settings > Apps > Termux and Termux:Boot > Battery > **Unrestricted** (wording differs by brand).
- Allow **autostart** for both, and lock Termux in the recent apps screen.
- Brand-specific steps: [dontkillmyapp.com](https://dontkillmyapp.com).

The bot sends a daily "alive" message at `heartbeat_hour` (default 08:00). If it stops arriving, Android killed the bot.

## Commands

```bash
./start.sh                # start in background (auto-restarts on crash)
./stop.sh                 # stop
./status.sh               # running? + last log lines
python bot.py --dry-run   # check once, print signals, send nothing
python bot.py --test      # send a Telegram test message
git pull && ./stop.sh && ./start.sh   # update to the latest version
```

## Configuration

Edit `config.json` (created from `config.example.json` on install), then restart with `./stop.sh && ./start.sh`.

| Key | Default | Meaning |
|---|---|---|
| `symbols` | BTC, ETH, SOL, BNB, XRP vs USDT | Binance spot symbols |
| `timeframes` | `15m`, `1h`, `4h` | Binance intervals (`5m`, `15m`, `1h`, `4h`, `1d`, ...) |
| `interval_minutes` | `5` | how often to check |
| `heartbeat_hour` | `8` | hour for the daily alive message, `null` to turn off |
| `strategy.rsi_period` | `8` | RSI length |
| `strategy.oversold` / `overbought` | `30` / `70` | RSI cross levels |
| `strategy.fib_level` | `0.618` | retracement level to watch |
| `strategy.swing_lookback` | `50` | candles used to find the swing high/low |
| `strategy.trend_sma` | `50` | trend filter length |
| `strategy.touch_window` | `3` | how many recent candles may touch the Fib level |

## Phone care

Charging 24/7 can swell the battery. Turn on the phone's charge limit or smart charging if it has one, keep it cool and out of a case, and away from anything flammable.

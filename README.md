# FiboRSI8 Bot

A small Telegram alert bot for the FiboRSI8 setup: Fibonacci retracement + RSI(8) with a trend filter. It watches crypto pairs on Binance public market data and messages you when a closed candle matches the rules.

Alerts only. It never places trades. Signals are not financial advice, so check the chart before acting.

Python standard library only, no `pip install` needed. Runs on:

- **Android phone** with Termux (good for an old backup phone running 24/7)
- **Linux**: an old laptop (Linux Mint, Ubuntu, Debian) or a VPS
- **macOS**, for testing

## Strategy rules

Checked on every **closed** candle, for every symbol and timeframe in `config.json`:

| | LONG | SHORT |
|---|---|---|
| Trend | close above SMA(50) | close below SMA(50) |
| Fibonacci | price touched the 61.8% pullback level of the last 50 candles' swing, within the last 3 candles | price touched the 61.8% rally level, within the last 3 candles |
| RSI(8) | crosses back above 30 | crosses back below 70 |
| Reference stop / target | swing low / swing high | swing high / swing low |

Each signal is sent once per candle. All numbers are configurable in `config.json` under `strategy`.

Alerts include a ready-made plan: entry (signal candle close), stop (swing low/high), a break-even instruction (move stop to entry after TP1), and take-profit levels at 1R, 2R and the swing target (levels beyond the swing target are dropped automatically). RSI and Fib values are included for confirmation.

## Step 1: Create the Telegram bot

Telegram bots are free. You make one by chatting with **@BotFather**, Telegram's official bot for creating bots.

1. Open Telegram and search for **@BotFather**. Pick the one with the blue verified tick; there are fakes.
2. Press **Start**, then send `/newbot`.
3. BotFather asks for a **name**. This is the display name, anything you like, for example `FiboRSI8 Alerts`.
4. BotFather asks for a **username**. It must be unique and end in `bot`, for example `yasin_fiborsi8_bot`. If it's taken, try another.
5. BotFather replies with a **token** that looks like `123456789:ABCdefGhIJKlmNoPQRstuVWxyz`. Copy it.
6. Open your new bot (BotFather's reply has a `t.me/...` link) and press **Start**. The bot can only message you after you have messaged it first.

The installer asks for the token and finds your **chat_id** for you. To find it by hand instead:

```bash
TG_TOKEN=<your token> python3 bot.py --get-chat-id
```

Or open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and look for `"chat":{"id": ...}`.

**Keep the token secret.** Anyone with it can control your bot. It is stored only in `.env`, which is gitignored. If it leaks, send `/revoke` to @BotFather to get a new one.

Optional BotFather commands: `/setuserpic` (bot photo), `/setdescription`, `/mybots` (manage your bots).

## Step 2: Install

### Android (Termux)

1. Install **Termux** and **Termux:Boot** from [F-Droid](https://f-droid.org/packages/com.termux/) or the [Termux GitHub releases](https://github.com/termux/termux-app/releases). Do not use the Play Store version of Termux, it is outdated.
2. In Termux:

   ```bash
   pkg install -y git
   git clone https://github.com/YsinHsim/fiborsi8.git
   cd fiborsi8
   ./install.sh
   ```

3. Stop Android from killing it:
   - Open the **Termux:Boot** app once.
   - Settings > Apps > Termux and Termux:Boot > Battery > **Unrestricted** (wording differs by brand).
   - Allow **autostart** for both, and lock Termux in the recent apps screen.
   - Brand-specific steps: [dontkillmyapp.com](https://dontkillmyapp.com).

### Linux (laptop or VPS)

```bash
sudo apt install -y python3 git
git clone https://github.com/YsinHsim/fiborsi8.git
cd fiborsi8
./install.sh
```

The installer adds a `@reboot` crontab entry so the bot starts after a reboot.

On a laptop, stop it sleeping when the lid closes: set `HandleLidSwitch=ignore` in `/etc/systemd/logind.conf`, then run `sudo systemctl restart systemd-logind`. Also turn off suspend in the power settings.

On a VPS, crypto exchanges block US server IPs. Pick a Singapore region.

### macOS

```bash
git clone https://github.com/YsinHsim/fiborsi8.git
cd fiborsi8
./install.sh
```

No auto-start on macOS. Run `./start.sh` after a reboot, and the bot only runs while the Mac is awake.

### What the installer does

1. Installs Python and git (Termux only).
2. Creates `config.json` from `config.example.json`.
3. Asks for your bot token, finds your chat_id, and saves both to `.env`.
4. Sets up auto-start (Termux:Boot on Android, crontab on Linux).
5. Sends a test message to your Telegram.
6. Starts the bot in the background.

## Commands

```bash
./start.sh                  # start in background (auto-restarts on crash)
./stop.sh                   # stop
./status.sh                 # running? + last log lines
./update.sh                 # pull the latest version, smoke test, restart
python3 bot.py --dry-run    # check once, print signals, send nothing
python3 bot.py --test       # send a Telegram test message
python3 bot.py --get-chat-id  # list chat_ids that messaged the bot
```

The bot sends a daily "alive" message at `heartbeat_hour` (default 08:00). If it stops arriving, the bot has stopped (on Android, usually the OS killed it).

## Configuration

Edit `config.json`, then restart with `./stop.sh && ./start.sh`.

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

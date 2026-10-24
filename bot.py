#!/usr/bin/env python3
"""FiboRSI8 signal bot.

Watches crypto pairs on Binance public market data, checks a Fibonacci
retracement + RSI(8) rule on closed candles, and sends Telegram alerts.

Standard library only, so it installs cleanly on Termux.

Usage:
    python bot.py            check once, send alerts
    python bot.py --loop     check every `interval_minutes` forever
    python bot.py --dry-run  check once, print signals, send nothing
    python bot.py --test     send a test Telegram message
    python bot.py --get-chat-id  list chat_ids that messaged the bot
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config.json")
ENV_PATH = os.path.join(ROOT, ".env")
STATE_PATH = os.path.join(ROOT, "state.json")

KLINES_URL = "https://data-api.binance.vision/api/v3/klines"


def report_status(config, state, errors):
    """POST bot status to the monitoring dashboard. Optional; silently skips
    if monitor_url/monitor_secret are not set in config.json."""
    url = config.get("monitor_url")
    secret = config.get("monitor_secret")
    if not url or not secret:
        return
    payload = {
        "ts": int(time.time() * 1000),
        "symbols": config["symbols"],
        "timeframes": config["timeframes"],
        "interval_minutes": config.get("interval_minutes", 5),
        "alerted": state.get("alerted", {}),
        "errors": errors[-20:],
    }
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {secret}"},
        )
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception as e:
        log(f"monitor report error: {e}")


def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def load_env(path=ENV_PATH):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def http_get_json(url, params, timeout=15):
    full = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full, headers={"User-Agent": "fiborsi8-bot"})
    last_err = None
    # One retry: phones drop TLS connections often, and waiting a whole
    # cycle for the next check is worse than waiting 3 seconds.
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError:
            raise  # server answered: 4xx/5xx, retrying won't help
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
            if attempt == 0:
                time.sleep(3)
    raise last_err


# --- Market data -----------------------------------------------------------

def fetch_closed_candles(symbol, timeframe, limit):
    """Return closed candles as dicts. The candle still forming is dropped."""
    rows = http_get_json(KLINES_URL, {"symbol": symbol, "interval": timeframe, "limit": limit + 1})
    now_ms = int(time.time() * 1000)
    candles = [
        {
            "open_time": int(r[0]),
            "open": float(r[1]),
            "high": float(r[2]),
            "low": float(r[3]),
            "close": float(r[4]),
            "close_time": int(r[6]),
        }
        for r in rows
    ]
    return [c for c in candles if c["close_time"] < now_ms]


# --- Indicators ------------------------------------------------------------

def rsi(closes, period):
    """Wilder's RSI, same as TradingView's ta.rsi. Returns a list aligned to closes."""
    out = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        change = closes[i] - closes[i - 1]
        gains += max(change, 0)
        losses += max(-change, 0)
    avg_gain, avg_loss = gains / period, losses / period
    out[period] = _rsi_value(avg_gain, avg_loss)
    for i in range(period + 1, len(closes)):
        change = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(change, 0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0)) / period
        out[i] = _rsi_value(avg_gain, avg_loss)
    return out


def _rsi_value(avg_gain, avg_loss):
    if avg_loss == 0:
        return 100.0
    return 100 - 100 / (1 + avg_gain / avg_loss)


def sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


# --- Strategy --------------------------------------------------------------

def check_signal(candles, s):
    """Apply the FiboRSI8 rule to the last closed candle. Returns a signal dict or None.

    LONG:  close above SMA(trend) + price touched the 61.8% pullback level within
           the last `touch_window` candles + RSI crosses back above `oversold`.
    SHORT: mirror image, using the 61.8% rally level and `overbought`.
    """
    need = max(s["swing_lookback"], s["trend_sma"], s["rsi_period"] + 2)
    if len(candles) < need:
        return None

    closes = [c["close"] for c in candles]
    r = rsi(closes, s["rsi_period"])
    rsi_now, rsi_prev = r[-1], r[-2]
    if rsi_now is None or rsi_prev is None:
        return None

    window = candles[-s["swing_lookback"]:]
    swing_high = max(c["high"] for c in window)
    swing_low = min(c["low"] for c in window)
    rng = swing_high - swing_low
    if rng <= 0:
        return None

    fib = s["fib_level"]
    long_level = swing_high - rng * fib    # pullback in an uptrend
    short_level = swing_low + rng * fib    # rally in a downtrend
    trend = sma(closes, s["trend_sma"])
    recent = candles[-s["touch_window"]:]
    last = candles[-1]

    if (
        last["close"] > trend
        and min(c["low"] for c in recent) <= long_level
        and rsi_prev < s["oversold"] <= rsi_now
    ):
        return {
            "side": "LONG",
            "price": last["close"],
            "rsi": rsi_now,
            "fib_price": long_level,
            "stop": swing_low,
            "target": swing_high,
            "open_time": last["open_time"],
        }

    if (
        last["close"] < trend
        and max(c["high"] for c in recent) >= short_level
        and rsi_prev > s["overbought"] >= rsi_now
    ):
        return {
            "side": "SHORT",
            "price": last["close"],
            "rsi": rsi_now,
            "fib_price": short_level,
            "stop": swing_high,
            "target": swing_low,
            "open_time": last["open_time"],
        }

    return None


# --- Telegram --------------------------------------------------------------

def send_telegram(text):
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT")
    if not token or not chat_id:
        raise RuntimeError("TG_TOKEN or TG_CHAT missing in .env")
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.load(resp)
    if not body.get("ok"):
        raise RuntimeError(f"Telegram error: {body}")


def get_chat_ids(token):
    """Return {chat_id: name} for chats that recently messaged the bot."""
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        body = http_get_json(url, {})
    except urllib.error.HTTPError as e:
        if e.code in (401, 404):
            raise RuntimeError("Telegram rejected the token. Copy it again from @BotFather.")
        raise
    chats = {}
    for update in body.get("result", []):
        msg = update.get("message") or update.get("channel_post") or {}
        chat = msg.get("chat")
        if chat:
            name = chat.get("title") or " ".join(
                filter(None, [chat.get("first_name"), chat.get("last_name")])
            ) or chat.get("username", "")
            chats[str(chat["id"])] = name
    return chats


def fmt_price(p):
    return f"{p:,.2f}" if p >= 100 else f"{p:.6g}"


def format_signal(symbol, timeframe, sig, fib_level):
    side = sig["side"]
    arrow = "🟢" if side == "LONG" else "🔴"
    action = "BUY" if side == "LONG" else "SELL"
    entry, stop, target = sig["price"], sig["stop"], sig["target"]
    risk = abs(entry - stop)
    if side == "LONG":
        tp3_name, stop_name = "swing high", "swing low"
        r_levels = [entry + risk, entry + 2 * risk]
        tps = [t for t in r_levels if t < target] + [target]
    else:
        tp3_name, stop_name = "swing low", "swing high"
        r_levels = [entry - risk, entry - 2 * risk]
        tps = [t for t in r_levels if t > target] + [target]
    p = fmt_price
    tp_lines = "".join(
        f"   TP{i + 1}: {p(t)} ({tp3_name if t == target else f'{i + 1}R'})\n"
        for i, t in enumerate(tps)
    )
    return (
        f"{arrow} FiboRSI8 {side}  {symbol} {timeframe}\n"
        f"\n"
        f"1. {action}: {p(entry)}\n"
        f"2. Stop: {p(stop)} ({stop_name})\n"
        f"3. Break even: after TP1 hits, move stop to {p(entry)}\n"
        f"4. Take profits ({'buy back' if side == 'SHORT' else 'sell'} in parts):\n"
        f"{tp_lines}"
        f"\n"
        f"RSI(8): {sig['rsi']:.1f} | Fib {fib_level * 100:.1f}%: {p(sig['fib_price'])}\n"
        f"Signal only, not advice. Check the chart first."
    )


# --- Main ------------------------------------------------------------------

def run_once(config, dry_run=False):
    state = load_json(STATE_PATH, {"alerted": {}, "heartbeat_day": None})
    s = config["strategy"]
    limit = max(s["swing_lookback"], s["trend_sma"]) + s["rsi_period"] * 10
    errors = []

    for symbol in config["symbols"]:
        for tf in config["timeframes"]:
            key = f"{symbol}:{tf}"
            try:
                candles = fetch_closed_candles(symbol, tf, limit)
                sig = check_signal(candles, s)
            except Exception as e:
                log(f"{key} error: {e}")
                errors.append(f"{key}: {e}")
                continue

            if not sig:
                continue
            if state["alerted"].get(key) == sig["open_time"]:
                continue  # already sent this candle

            msg = format_signal(symbol, tf, sig, s["fib_level"])
            log(f"{key} {sig['side']} @ {sig['price']}")
            if dry_run:
                print(msg + "\n")
                continue
            try:
                send_telegram(msg)
                state["alerted"][key] = sig["open_time"]
            except Exception as e:
                log(f"{key} telegram error: {e}")

    hb_hour = config.get("heartbeat_hour")
    today = datetime.now().strftime("%Y-%m-%d")
    if (
        not dry_run
        and hb_hour is not None
        and datetime.now().hour >= hb_hour
        and state.get("heartbeat_day") != today
    ):
        try:
            dash = config.get("monitor_url", "").replace("/api/status", "")
            send_telegram(
                f"✅ FiboRSI8 bot alive. Watching {len(config['symbols'])} pairs on "
                f"{', '.join(config['timeframes'])}."
                + (f"\nDashboard: {dash}" if dash else "")
            )
            state["heartbeat_day"] = today
        except Exception as e:
            log(f"heartbeat error: {e}")

    if not dry_run:
        save_json(STATE_PATH, state)
        report_status(config, state, errors)


def main():
    parser = argparse.ArgumentParser(description="FiboRSI8 Telegram signal bot")
    parser.add_argument("--loop", action="store_true", help="run forever")
    parser.add_argument("--dry-run", action="store_true", help="print signals, send nothing")
    parser.add_argument("--test", action="store_true", help="send a test Telegram message")
    parser.add_argument("--get-chat-id", action="store_true",
                        help="list chat_ids that messaged the bot (needs TG_TOKEN)")
    args = parser.parse_args()

    load_env()

    if args.get_chat_id:
        token = os.environ.get("TG_TOKEN")
        if not token:
            sys.exit("TG_TOKEN missing. Put it in .env or run: TG_TOKEN=... python3 bot.py --get-chat-id")
        try:
            chats = get_chat_ids(token)
        except Exception as e:
            sys.exit(str(e))
        if not chats:
            sys.exit("No messages found. Send any message to your bot in Telegram, then run this again.")
        for chat_id, name in chats.items():
            print(f"{chat_id}\t{name}")
        return

    config = load_json(CONFIG_PATH, None)
    if config is None:
        sys.exit(f"Missing or invalid {CONFIG_PATH}. Copy config.example.json to config.json.")

    if args.test:
        send_telegram("👋 FiboRSI8 bot test message. Telegram is working.")
        log("Test message sent.")
        return

    if not args.loop:
        run_once(config, dry_run=args.dry_run)
        return

    interval = config.get("interval_minutes", 5) * 60
    log(f"Loop started, every {interval // 60} min.")
    while True:
        try:
            run_once(config, dry_run=args.dry_run)
        except Exception as e:
            log(f"run error: {e}")
        # Sleep until 5s after the next interval boundary (so the candle has
        # closed). Sleep in short chunks: on Android, doze can stretch one
        # long sleep far past the boundary and skip a whole cycle.
        deadline = time.time() + interval - (time.time() % interval) + 5
        while time.time() < deadline:
            time.sleep(min(60, deadline - time.time()))


if __name__ == "__main__":
    main()

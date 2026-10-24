#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")"

if [ -f bot.pid ] && kill -0 "$(cat bot.pid)" 2>/dev/null; then
  pkill -P "$(cat bot.pid)" 2>/dev/null
  kill "$(cat bot.pid)"
  echo "Stopped."
else
  echo "Not running."
fi
rm -f bot.pid
command -v termux-wake-unlock >/dev/null && termux-wake-unlock

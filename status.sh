#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")"

if [ -f bot.pid ] && kill -0 "$(cat bot.pid)" 2>/dev/null; then
  echo "Running (pid $(cat bot.pid))."
else
  echo "Not running. Start with ./start.sh"
fi
echo "--- last 10 log lines ---"
tail -n 10 bot.log 2>/dev/null

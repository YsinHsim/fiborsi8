#!/data/data/com.termux/files/usr/bin/bash
# Start the bot in the background. Restarts it if it crashes.
cd "$(dirname "$0")"

if [ -f bot.pid ] && kill -0 "$(cat bot.pid)" 2>/dev/null; then
  echo "Already running (pid $(cat bot.pid))."
  exit 0
fi

command -v termux-wake-lock >/dev/null && termux-wake-lock

nohup bash -c 'while true; do python bot.py --loop; echo "bot exited, restarting in 30s"; sleep 30; done' \
  >> bot.log 2>&1 &
echo $! > bot.pid
echo "Started (pid $!). Logs: bot.log"

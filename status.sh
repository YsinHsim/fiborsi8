#!/usr/bin/env bash
cd "$(dirname "$0")"

if [ -f bot.pid ] && kill -0 "$(cat bot.pid)" 2>/dev/null; then
  echo "Running (pid $(cat bot.pid))."
else
  echo "Not running. Start with ./start.sh"
fi

# Dashboard link, if monitoring is configured
DASH=$(python3 -c "
import json
url = json.load(open('config.json')).get('monitor_url', '')
print(url.replace('/api/status', '') if url else '')
" 2>/dev/null)
[ -n "$DASH" ] && echo "Dashboard: $DASH"

echo "--- last 10 log lines ---"
tail -n 10 bot.log 2>/dev/null

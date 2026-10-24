#!/usr/bin/env bash
# FiboRSI8 installer for Termux (Android), Linux and macOS.
# Run from the repo folder: ./install.sh
set -e

cd "$(dirname "$0")"
DIR="$(pwd)"

if [ -n "$TERMUX_VERSION" ] || [ -d /data/data/com.termux ]; then
  PLATFORM=termux
elif [ "$(uname)" = "Darwin" ]; then
  PLATFORM=macos
else
  PLATFORM=linux
fi
echo "==> Platform: $PLATFORM"

if [ "$PLATFORM" = "termux" ]; then
  echo "==> Installing packages"
  pkg update -y
  pkg install -y python git
fi

if ! command -v python3 >/dev/null; then
  echo "python3 not found. Install it first:"
  echo "  Linux (Debian/Ubuntu/Mint): sudo apt install python3"
  echo "  macOS: xcode-select --install   (or brew install python)"
  exit 1
fi

if [ ! -f config.json ]; then
  cp config.example.json config.json
  echo "==> Created config.json (edit symbols/timeframes later if you want)"
fi

if [ ! -f .env ]; then
  echo
  echo "==> Telegram setup (see README: 'Create the Telegram bot')"
  read -rp "Bot token from @BotFather: " TOKEN
  echo
  echo "Now open your bot in Telegram, press Start (or send any message)."
  read -rp "Press Enter when done... " _
  CHATS="$(TG_TOKEN="$TOKEN" python3 bot.py --get-chat-id)" || exit 1
  echo "$CHATS"
  CHAT="$(echo "$CHATS" | head -n 1 | cut -f1)"
  read -rp "Use chat_id $CHAT? [Y/n] " OK
  if [ "$OK" = "n" ] || [ "$OK" = "N" ]; then
    read -rp "Type the chat_id to use: " CHAT
  fi
  printf 'TG_TOKEN=%s\nTG_CHAT=%s\n' "$TOKEN" "$CHAT" > .env
  chmod 600 .env
fi

chmod +x bot.py start.sh stop.sh status.sh

echo "==> Setting up auto-start"
case "$PLATFORM" in
  termux)
    mkdir -p ~/.termux/boot
    cat > ~/.termux/boot/fiborsi8.sh <<EOF
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
"$DIR/start.sh"
EOF
    chmod +x ~/.termux/boot/fiborsi8.sh
    echo "Boot script added (needs the Termux:Boot app)."
    ;;
  linux)
    if command -v crontab >/dev/null; then
      ( crontab -l 2>/dev/null | grep -v 'fiborsi8/start.sh'; echo "@reboot sleep 30 && $DIR/start.sh" ) | crontab -
      echo "Added @reboot entry to your crontab."
    else
      echo "crontab not found, skipping. Run ./start.sh after each reboot."
    fi
    ;;
  macos)
    echo "Skipped on macOS. Run ./start.sh after each reboot, and keep the Mac awake."
    ;;
esac

echo "==> Sending test message"
python3 bot.py --test

echo "==> Starting bot"
./start.sh

echo
echo "Done. Check it with ./status.sh. Logs are in bot.log."
if [ "$PLATFORM" = "termux" ]; then
  cat <<'EOF'

Last steps on the phone:
  1. Open the Termux:Boot app once so Android lets it run on boot.
  2. Settings > Apps > Termux (and Termux:Boot) > Battery > Unrestricted.
  3. Allow autostart for both, and lock Termux in the recent apps screen.
EOF
elif [ "$PLATFORM" = "linux" ]; then
  echo "Laptop? Stop it sleeping on lid close: set HandleLidSwitch=ignore in /etc/systemd/logind.conf"
fi

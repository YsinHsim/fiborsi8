#!/data/data/com.termux/files/usr/bin/bash
# FiboRSI8 installer for Termux. Run from the repo folder: ./install.sh
set -e

cd "$(dirname "$0")"
DIR="$(pwd)"

echo "==> Installing packages"
pkg update -y
pkg install -y python git

if [ ! -f config.json ]; then
  cp config.example.json config.json
  echo "==> Created config.json (edit symbols/timeframes later if you want)"
fi

if [ ! -f .env ]; then
  echo "==> Telegram setup"
  read -rp "Bot token from @BotFather: " TOKEN
  read -rp "Your chat_id: " CHAT
  printf 'TG_TOKEN=%s\nTG_CHAT=%s\n' "$TOKEN" "$CHAT" > .env
  chmod 600 .env
fi

chmod +x start.sh stop.sh status.sh

echo "==> Setting up auto-start on boot (needs the Termux:Boot app)"
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/fiborsi8.sh <<EOF
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
"$DIR/start.sh"
EOF
chmod +x ~/.termux/boot/fiborsi8.sh

echo "==> Sending test message"
python bot.py --test

echo "==> Starting bot"
./start.sh

cat <<'EOF'

Done. Next, on the phone:
  1. Open the Termux:Boot app once so Android lets it run on boot.
  2. Settings > Apps > Termux (and Termux:Boot) > Battery > Unrestricted.
  3. Allow autostart for both, and lock Termux in the recent apps screen.

Check it with ./status.sh. Logs are in bot.log.
EOF

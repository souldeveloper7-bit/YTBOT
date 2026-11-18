\
#!/bin/sh
set -eu

: "${TELEGRAM_API_ID:?Set TELEGRAM_API_ID from my.telegram.org}"
: "${TELEGRAM_API_HASH:?Set TELEGRAM_API_HASH from my.telegram.org}"
: "${BOT_TOKEN:?Set BOT_TOKEN from BotFather}"

mkdir -p /data/telegram-bot-api /data/downloads

telegram-bot-api \
  --api-id="$TELEGRAM_API_ID" \
  --api-hash="$TELEGRAM_API_HASH" \
  --local \
  --http-port=8081 \
  --dir=/data/telegram-bot-api &

API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT INT TERM

echo "Waiting for local Telegram Bot API..."
i=0
until curl -fsS "http://127.0.0.1:8081/bot${BOT_TOKEN}/getMe" >/dev/null; do
  i=$((i + 1))
  if [ "$i" -ge 60 ]; then
    echo "Local Bot API did not become ready"
    exit 1
  fi
  sleep 2
done

echo "Local Telegram Bot API ready; starting downloader bot"
exec python bot.py

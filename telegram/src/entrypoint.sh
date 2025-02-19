#!/bin/bash
set -e

# Загрузка Telegram Token
if [ -f /run/secrets/telegram_token ]; then
  export TELEGRAM_TOKEN=$(cat /run/secrets/telegram_token)
  echo "✅ Telegram Token загружен."
else
  echo "❌ Telegram Token не найден!" && exit 1
fi

# Загрузка GPT API URL
if [ -f /run/secrets/gpt_api_url ]; then
  export GPT_API_URL=$(cat /run/secrets/gpt_api_url)
  echo "✅ GPT API URL загружен: $GPT_API_URL"
else
  echo "❌ GPT API URL не найден!" && exit 1
fi

# Проверка перед запуском
echo "⚙️ Проверка переменных окружения:"
echo "TELEGRAM_TOKEN: $TELEGRAM_TOKEN"
echo "GPT_API_URL: $GPT_API_URL"

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

python3 -u app.py

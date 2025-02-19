#!/bin/bash
set -e

# Чтение GPT API ключа из монтируемого секрета
if [ -f /run/secrets/gpt_api_key ]; then
  export GPT_API_KEY=$(cat /run/secrets/gpt_api_key | tr -d '\r')
  echo "✅ GPT API Key загружен: $GPT_API_KEY"
else
  echo "⚠️ GPT API Key не найден!"
  exit 1
fi

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Проверка переменной перед запуском
echo "⚙️ Проверка переменной окружения GPT_API_KEY: $GPT_API_KEY"

python3 -m uvicorn main:app --workers 1 --host 0.0.0.0 --port 9001

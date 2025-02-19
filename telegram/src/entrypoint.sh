#!/bin/bash

# Ожидаем запуска PostgreSQL
echo "Ожидание PostgreSQL..."
until nc -z $DB_HOST $DB_PORT; do
  sleep 1
done
echo "PostgreSQL запущен. Запускаем бота."

set -e

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

python3 -u app.py

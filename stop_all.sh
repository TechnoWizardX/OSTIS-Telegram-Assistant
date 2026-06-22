#!/usr/bin/env bash
# stop_all.sh — остановка всех сервисов OSTIS Assistant
# Просто вызывает start_all.sh stop

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/start_all.sh" stop

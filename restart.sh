#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$SCRIPT_DIR/.pids"

echo "🛑 Останавливаем все терминалы..."

if [ -d "$PID_DIR" ]; then
    for pid_file in "$PID_DIR"/*.pid; do
        [ -f "$pid_file" ] || continue
        name=$(basename "$pid_file" .pid)
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo "  → Завершён $name (PID $pid)"
        fi
        rm -f "$pid_file"
    done
else
    echo "  ⚠️  PID директория не найдена — продолжаем"
fi

sleep 1

echo ""
echo "🚀 Перезапускаем через launch.sh..."
sleep 1

exec "$SCRIPT_DIR/launch.sh"
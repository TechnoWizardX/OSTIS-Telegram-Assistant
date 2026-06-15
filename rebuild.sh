#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$SCRIPT_DIR/.pids"

open_terminal() {
    local name="$1"
    local cmd="$2"
    mkdir -p "$PID_DIR"

    if command -v kitty &>/dev/null; then
        kitty --title "$name" bash -c "$cmd; exec bash" &
    elif command -v gnome-terminal &>/dev/null; then
        gnome-terminal --title="$name" -- bash -c "$cmd; exec bash" &
    elif command -v konsole &>/dev/null; then
        konsole --new-tab -p tabtitle="$name" -e bash -c "$cmd; exec bash" &
    elif command -v xfce4-terminal &>/dev/null; then
        xfce4-terminal --title="$name" -e "bash -c '$cmd; exec bash'" &
    elif command -v xterm &>/dev/null; then
        xterm -title "$name" -e bash -c "$cmd; exec bash" &
    elif command -v osascript &>/dev/null; then
        osascript -e "tell application \"Terminal\" to do script \"$cmd\"" &
    else
        echo "❌ Не найден эмулятор терминала"
        exit 1
    fi

    echo $! > "$PID_DIR/$name.pid"
    echo "  ✅ $name перезапущен (PID $!)"
}

echo "🔄 Перезапуск terminal1 (build_kb → machine)..."

PID_FILE="$PID_DIR/terminal1.pid"
if [ -f "$PID_FILE" ]; then
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null
        echo "  → Завершён процесс PID $pid"
    fi
    rm -f "$PID_FILE"
else
    echo "  ⚠️  PID файл terminal1 не найден — продолжаем"
fi

sleep 1

open_terminal "terminal1" "cd '$SCRIPT_DIR' && ./scripts/start.sh build_kb && ./scripts/start.sh machine"

echo ""
echo "✅ rebuild завершён"
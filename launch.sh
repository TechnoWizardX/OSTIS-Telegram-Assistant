#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$SCRIPT_DIR/.pids"
mkdir -p "$PID_DIR"

open_terminal() {
    local name="$1"
    local cmd="$2"

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
        echo "❌ Не найден эмулятор терминала (kitty / gnome-terminal / konsole / xfce4-terminal / xterm)"
        exit 1
    fi

    echo $! > "$PID_DIR/$name.pid"
    echo "  ✅ $name запущен (PID $!)"
}

echo "🚀 Запускаем все терминалы..."

open_terminal "terminal1" "cd '$SCRIPT_DIR' && ./scripts/start.sh build_kb && ./scripts/start.sh machine"
sleep 0.3
open_terminal "terminal2" "cd '$SCRIPT_DIR' && ./scripts/start.sh web"
sleep 0.3
open_terminal "terminal3" "cd '$SCRIPT_DIR' && ./scripts/start.sh interface"
sleep 0,3
#open_terminal "terminal4" "cd '$SCRIPT_DIR' && ./scripts/start.sh py_server"
echo ""
echo "✅ Все терминалы запущены"
#!/bin/bash

# Определяем терминальный эмулятор
get_terminal() {
    for term in gnome-terminal konsole xterm xfce4-terminal tilix alacritty; do
        if command -v "$term" &>/dev/null; then
            echo "$term"
            return
        fi
    done
    echo ""
}

TERM_APP=$(get_terminal)

if [ -z "$TERM_APP" ]; then
    echo "❌ Не найден терминальный эмулятор. Установите один из: gnome-terminal, konsole, xterm, xfce4-terminal, tilix, alacritty"
    exit 1
fi

echo "🚀 Запуск всех процессов через: $TERM_APP"

# Функция для открытия вкладки/окна в зависимости от терминала
open_terminal() {
    local title="$1"
    local cmd="$2"

    case "$TERM_APP" in
        gnome-terminal)
            gnome-terminal --title="$title" -- bash -c "$cmd; exec bash" &
            ;;
        konsole)
            konsole --new-tab -p tabtitle="$title" -e bash -c "$cmd; exec bash" &
            ;;
        tilix)
            tilix --title="$title" -e bash -c "$cmd; exec bash" &
            ;;
        xfce4-terminal)
            xfce4-terminal --title="$title" -e "bash -c '$cmd; exec bash'" &
            ;;
        alacritty)
            alacritty --title "$title" -e bash -c "$cmd; exec bash" &
            ;;
        xterm)
            xterm -title "$title" -e bash -c "$cmd; exec bash" &
            ;;
    esac
}

# Терминал 1: build_kb затем machine (последовательно)
open_terminal "Terminal 1 — build_kb & machine" \
    "echo '=== [1/2] build_kb ===' && ./scripts/start.sh build_kb && echo '=== [2/2] machine ===' && ./scripts/start.sh machine"

sleep 0.5

# Терминал 2: web
open_terminal "Terminal 2 — web" \
    "echo '=== web ===' && ./scripts/start.sh web"

sleep 0.5

# Терминал 3: interface
open_terminal "Terminal 3 — interface" \
    "echo '=== interface ===' && ./scripts/start.sh interface"

echo "✅ Все терминалы запущены."

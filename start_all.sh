#!/usr/bin/env bash
set -eo pipefail

# ============================================================
#  start_all.sh — полный запуск Telegram-бота OSTIS Assistant
#
#  Порядок:
#    1. Сборка базы знаний (kb.bin)
#    2. SC-machine    (WebSocket :8090)
#    3. SC-web        (веб-сервер)
#    4. Problem-solver (sc-kpm модули: MessageClassify, TopicInfo)
#    5. Telegram-бот
#
#  Использование:
#    ./start_all.sh                  # запустить всё
#    ./start_all.sh --no-web         # без SC-web
#    ./start_all.sh --no-py-server   # без Python problem-solver (только C++ Nika)
#    ./start_all.sh stop             # остановить всё
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$SCRIPT_DIR/.pids"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$PID_DIR" "$LOG_DIR"

# --------------- конфигурация ---------------
SC_MACHINE_PORT=8090
SC_MACHINE_HOST="localhost"

# пути к установленным компонентам
INSTALL_DIR="$SCRIPT_DIR/install"
SC_MACHINE_DIR="$INSTALL_DIR/sc-machine"
SC_MACHINE_BIN="$SC_MACHINE_DIR/bin/sc-machine"
SC_BUILDER_BIN="$SC_MACHINE_DIR/bin/sc-builder"
SC_MACHINE_LIB="$SC_MACHINE_DIR/lib"
NIKA_EXT="$INSTALL_DIR/nika/lib/extensions"
SC_MACHINE_EXT="$SC_MACHINE_DIR/lib/extensions"
FIXED_SEARCH_LIB="$INSTALL_DIR/fixed-search-strategy-template-processing-lib"

# виртуальные окружения
SC_WEB_DIR="$SCRIPT_DIR/sc-web"
SC_WEB_VENV="$SC_WEB_DIR/.venv"
PS_VENV="$SCRIPT_DIR/problem-solver/py/.venv"

# флаги
SKIP_WEB=false
SKIP_PY_SERVER=false
STOP_MODE=false
CLEANED_UP=false

# --------------- trap: cleanup on any exit ---------------
cleanup() {
    if $CLEANED_UP; then return; fi
    CLEANED_UP=true
    echo ""
    echo "🛑 Останавливаем все сервисы..."
    for f in "$PID_DIR"/*.pid; do
        [ -f "$f" ] || continue
        name=$(basename "$f" .pid)
        pid=$(cat "$f")
        if kill -0 "$pid" 2>/dev/null; then
            kill -TERM -- -"$pid" 2>/dev/null || kill "$pid" 2>/dev/null
            echo "  → $name остановлен"
        fi
        rm -f "$f"
    done
    echo "Готово."
}
trap cleanup EXIT SIGINT SIGTERM

# --------------- разбор аргументов ---------------
for arg in "$@"; do
    case "$arg" in
        --no-web)        SKIP_WEB=true ;;
        --no-py-server)  SKIP_PY_SERVER=true ;;
        stop)            STOP_MODE=true ;;
        --help|-h)
            echo "Использование: $0 [--no-web] [--no-py-server] [stop]"
            echo "  --no-web          не запускать SC-web"
            echo "  --no-py-server    не запускать Python problem-solver (только C++ Nika)"
            echo "  stop              остановить все сервисы"
            CLEANED_UP=true; exit 0 ;;
    esac
done

# --------------- вычисляем нумерацию шагов ---------------
TOTAL_STEPS=3                      # build_kb + machine + tgbot (всегда)
if ! $SKIP_WEB; then TOTAL_STEPS=$((TOTAL_STEPS + 1)); fi
if ! $SKIP_PY_SERVER; then TOTAL_STEPS=$((TOTAL_STEPS + 1)); fi
CURRENT_STEP=0
next_step() { CURRENT_STEP=$((CURRENT_STEP + 1)); echo "Шаг $CURRENT_STEP/$TOTAL_STEPS"; }

# --------------- остановка ---------------
if $STOP_MODE; then
    echo "🛑 Останавливаем все сервисы..."
    STOPPED=0
    if [ -d "$PID_DIR" ]; then
        # Убиваем в обратном порядке: tgbot → py_server → web → machine
        for name in tgbot py_server web machine; do
            pid_file="$PID_DIR/$name.pid"
            if [ -f "$pid_file" ]; then
                pid=$(cat "$pid_file")
                if kill -0 "$pid" 2>/dev/null; then
                    # Убиваем группу процессов (PID со знаком минус)
                    kill -TERM -- -"$pid" 2>/dev/null || kill "$pid" 2>/dev/null
                    echo "  ✅ $name (PID $pid) остановлен"
                    STOPPED=$((STOPPED + 1))
                else
                    echo "  ⚠️  $name (PID $pid) уже не работает"
                fi
                rm -f "$pid_file"
            fi
        done
    fi
    # Зачистка осиротевших процессов на порту 8090
    ORPHAN_PID=$(lsof -ti :$SC_MACHINE_PORT 2>/dev/null || true)
    if [ -n "$ORPHAN_PID" ]; then
        echo "  ⚠️  Обнаружен процесс на порту $SC_MACHINE_PORT (PID $ORPHAN_PID) — убиваю"
        kill "$ORPHAN_PID" 2>/dev/null || true
        sleep 1
    fi
    if [ $STOPPED -eq 0 ] && [ -z "$ORPHAN_PID" ]; then
        echo "  Ничего не запущено."
    fi
    echo "Готово."
    CLEANED_UP=true
    exit 0
fi

# --------------- проверки окружения ---------------
echo "🔍 Проверка окружения..."

# 1. Очистка stale PID-файлов от предыдущих крашей
if ls "$PID_DIR"/*.pid >/dev/null 2>&1; then
    echo "⚠️  Найдены старые PID-файлы от предыдущего запуска. Чищу..."
    for f in "$PID_DIR"/*.pid; do
        [ -f "$f" ] || continue
        old_pid=$(cat "$f" 2>/dev/null || true)
        if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
            echo "  → Процесс $old_pid ещё жив — убиваю"
            kill -TERM -- -"$old_pid" 2>/dev/null || kill "$old_pid" 2>/dev/null || true
        fi
        rm -f "$f"
    done
fi

# Даём TIME_WAIT закрыться после kill старых процессов
sleep 1

# 2. Проверка: порт уже занят?
if (echo >/dev/tcp/$SC_MACHINE_HOST/$SC_MACHINE_PORT) 2>/dev/null; then
    echo "❌ Порт $SC_MACHINE_PORT уже занят! Останови старый процесс:"
    echo "   lsof -i :$SC_MACHINE_PORT"
    echo "   или $0 stop"
    CLEANED_UP=true
    exit 1
fi

# 3. Проверка бинарников
if [ ! -f "$SC_MACHINE_BIN" ]; then
    echo "❌ sc-machine не найден: $SC_MACHINE_BIN"
    echo "   Запусти scripts/install_cxx_problem_solver.sh"
    CLEANED_UP=true
    exit 1
fi
if [ ! -f "$SC_BUILDER_BIN" ]; then
    echo "❌ sc-builder не найден: $SC_BUILDER_BIN"
    CLEANED_UP=true
    exit 1
fi

# 4. Проверка sc-web
if ! $SKIP_WEB; then
    if [ ! -d "$SC_WEB_DIR" ]; then
        echo "⚠️  sc-web директория не найдена: $SC_WEB_DIR"
        echo "   SC-web не будет запущен."
        SKIP_WEB=true
    elif [ ! -d "$SC_WEB_VENV" ]; then
        echo "⚠️  sc-web venv не найден: $SC_WEB_VENV"
        echo "   SC-web не будет запущен."
        SKIP_WEB=true
    fi
fi

# 5. Проверка problem-solver
if ! $SKIP_PY_SERVER; then
    if [ ! -d "$PS_VENV" ]; then
        echo "❌ problem-solver venv не найден: $PS_VENV"
        CLEANED_UP=true
        exit 1
    fi
fi

# 6. Загрузка .env с токеном бота
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env" 2>/dev/null || true
    set +a
fi
if [ -z "${TG_BOT_TOKEN:-}${TELEGRAM_BOT_TOKEN:-}" ]; then
    echo "⚠️  TG_BOT_TOKEN/TELEGRAM_BOT_TOKEN не задан!"
    echo "   Создай .env файл с TG_BOT_TOKEN=... или экспортируй переменную."
    echo "   Бот будет запущен, но не сможет подключиться к Telegram."
fi

echo "✅ Окружение готово"
echo ""

# --------------- функция: ждать порт ---------------
wait_for_port() {
    local host="$1" port="$2" service="$3" timeout="${4:-90}"
    printf "⏳ Ожидание %s на %s:%s " "$service" "$host" "$port"
    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if (echo >/dev/tcp/"$host"/"$port") 2>/dev/null; then
            echo " ✅ (${elapsed}с)"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
        printf "." >&2
    done
    echo " ❌ ТАЙМАУТ (${timeout}с)"
    return 1
}

# --------------- функция: запустить в фоне с PID ---------------
# Процесс запускается в своей группе (setsid), чтобы kill -TERM -- -$pid
# убивал всех детей разом.
launch_bg() {
    local name="$1"; shift
    echo "🚀 Запуск $name..."
    setsid "$@" > "$LOG_DIR/$name.log" 2>&1 &
    local pid=$!
    echo $pid > "$PID_DIR/$name.pid"
    echo "  → PID $pid, лог: $LOG_DIR/$name.log"
}

# --------------- Шаг 1: сборка базы знаний ---------------
echo "═══════════════════════════════════════════"
echo "📦 $(next_step): Сборка базы знаний"
echo "═══════════════════════════════════════════"

BUILD_LOG="$LOG_DIR/build_kb.log"
echo "  Лог сборки: $BUILD_LOG"

LD_LIBRARY_PATH="$FIXED_SEARCH_LIB/lib:$SC_MACHINE_LIB:$LD_LIBRARY_PATH" \
    "$SC_BUILDER_BIN" -i repo-patch.path -o kb.bin --clear > "$BUILD_LOG" 2>&1

LD_LIBRARY_PATH="$FIXED_SEARCH_LIB/lib:$SC_MACHINE_LIB:$LD_LIBRARY_PATH" \
    "$SC_BUILDER_BIN" -i repo.path -o kb.bin >> "$BUILD_LOG" 2>&1

# Показываем последние строки лога (ошибки будут видны)
tail -5 "$BUILD_LOG"
echo "✅ База знаний собрана (kb.bin)"
echo ""

# --------------- Шаг 2: SC-machine ---------------
echo "═══════════════════════════════════════════"
echo "⚙️  $(next_step): SC-machine"
echo "═══════════════════════════════════════════"

launch_bg "machine" env \
    LD_LIBRARY_PATH="$FIXED_SEARCH_LIB/lib:$SC_MACHINE_LIB:$LD_LIBRARY_PATH" \
    "$SC_MACHINE_BIN" \
    -s kb.bin \
    -e "$SC_MACHINE_EXT;$NIKA_EXT" \
    -c nika.ini

if ! wait_for_port "$SC_MACHINE_HOST" "$SC_MACHINE_PORT" "SC-machine" 90; then
    echo "❌ SC-machine не запустился. Лог: $LOG_DIR/machine.log"
    echo "   Последние строки:"
    tail -20 "$LOG_DIR/machine.log"
    exit 1
fi

# Даём Nika время загрузить production-индексы после открытия порта.
# Без этой паузы первое сообщение всегда попадает в concept_unknown_message.
echo "⏳ Прогрев Nika (5 секунд)..."
sleep 5

# --------------- Шаг 3: SC-web ---------------
if ! $SKIP_WEB; then
    echo ""
    echo "═══════════════════════════════════════════"
    echo "🌐 $(next_step): SC-web"
    echo "═══════════════════════════════════════════"

    launch_bg "web" bash -c "
        cd '$SC_WEB_DIR' || exit 1
        source '$SC_WEB_VENV/bin/activate'
        exec python3 server/app.py
    "
    sleep 2
    echo "✅ SC-web запущен"
else
    echo ""
    echo "⏭️  SC-web пропущен (--no-web)"
fi

# --------------- Шаг: Problem-solver ---------------
if ! $SKIP_PY_SERVER; then
    echo ""
    echo "═══════════════════════════════════════════"
    echo "🧠 $(next_step): Problem-solver (sc-kpm модули)"
    echo "═══════════════════════════════════════════"

    launch_bg "py_server" bash -c "
        cd '$SCRIPT_DIR/problem-solver/py' || exit 1
        source '$PS_VENV/bin/activate'
        exec python3 server.py
    "
    sleep 3
    echo "✅ Problem-solver запущен"
else
    echo ""
    echo "⏭️  Problem-solver пропущен (--no-py-server)"
fi

# --------------- Шаг N: Telegram-бот ---------------
echo ""
echo "═══════════════════════════════════════════"
echo "🤖 $(next_step): Telegram-бот"
echo "═══════════════════════════════════════════"

launch_bg "tgbot" bash -c "
    cd '$SCRIPT_DIR/tgbot' || exit 1
    source '$PS_VENV/bin/activate'
    exec python3 bot.py
"
sleep 2

# Проверяем, что бот не упал сразу
if [ -f "$PID_DIR/tgbot.pid" ]; then
    tgbot_pid=$(cat "$PID_DIR/tgbot.pid")
    if kill -0 "$tgbot_pid" 2>/dev/null; then
        echo "✅ Telegram-бот запущен"
    else
        echo "❌ Telegram-бот упал при старте. Лог: $LOG_DIR/tgbot.log"
        echo ""
        tail -20 "$LOG_DIR/tgbot.log"
        exit 1
    fi
fi

# --------------- финал ---------------
echo ""
echo "═══════════════════════════════════════════"
echo "✅ ВСЁ ЗАПУЩЕНО"
echo "═══════════════════════════════════════════"
echo ""
echo "  Сервисы (PID в $PID_DIR/):"
for f in "$PID_DIR"/*.pid; do
    [ -f "$f" ] || continue
    name=$(basename "$f" .pid)
    pid=$(cat "$f")
    status="✓"
    kill -0 "$pid" 2>/dev/null || status="✗ УПАЛ"
    printf "    %-12s  PID %-6s  %s\n" "$name" "$pid" "$status"
done
echo ""
echo "  Логи: $LOG_DIR/"
echo "  Остановить всё: $0 stop"
echo ""
echo "  Нажми Ctrl+C чтобы остановить всё и выйти."
echo ""

# --------------- обработка Ctrl+C ---------------
# Trap уже установлен в начале скрипта (cleanup на EXIT/SIGINT/SIGTERM).
# Здесь НИЧЕГО не делаем — cleanup вызывается автоматически.

# Держим скрипт живым, пока работает хотя бы один сервис
while true; do
    any_alive=false
    for f in "$PID_DIR"/*.pid; do
        [ -f "$f" ] || continue
        pid=$(cat "$f")
        if kill -0 "$pid" 2>/dev/null; then
            any_alive=true
            break
        fi
    done
    if ! $any_alive; then
        echo ""
        echo "⚠️  Все сервисы остановились. Выход."
        CLEANED_UP=true
        exit 0
    fi
    sleep 5
done

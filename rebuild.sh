#!/bin/bash

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

pkill -f "kitty.*KB_MACHINE"

sleep 1

kitty --title KB_MACHINE bash -c "
cd '$PROJECT_DIR'
./scripts/start.sh build_kb
./scripts/start.sh machine
exec bash
" &
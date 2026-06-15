#!/bin/bash

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

bash --title KB_MACHINE bash -c "
cd '$PROJECT_DIR'
./scripts/start.sh build_kb
./scripts/start.sh machine
exec bash
" &

bash --title WEB bash -c "
cd '$PROJECT_DIR'
./scripts/start.sh web
exec bash
" &

bash --title INTERFACE bash -c "
cd '$PROJECT_DIR'
./scripts/start.sh interface
exec bash
" &
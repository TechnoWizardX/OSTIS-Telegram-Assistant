#!/bin/bash

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

pkill -f "bash.*KB_MACHINE"
pkill -f "bash.*WEB"
pkill -f "bash.*INTERFACE"

sleep 1

"$PROJECT_DIR/launch.sh"
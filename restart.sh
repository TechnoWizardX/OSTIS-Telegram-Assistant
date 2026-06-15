#!/bin/bash

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

pkill -f "kitty.*KB_MACHINE"
pkill -f "kitty.*WEB"
pkill -f "kitty.*INTERFACE"

sleep 1

"$PROJECT_DIR/launch.sh"
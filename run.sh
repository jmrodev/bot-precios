#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

if [ -f "$DIR/.venv/bin/python" ]; then
    exec "$DIR/.venv/bin/python" bot.py
else
    exec python3 bot.py
fi

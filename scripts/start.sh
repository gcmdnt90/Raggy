#!/bin/bash
# Banco — start script (Linux/Mac)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

if [ ! -f ".env" ]; then
    echo "First run: starting setup wizard..."
    python scripts/setup_wizard.py
fi

echo "Banco          http://127.0.0.1:8501"
echo "Stage console  http://127.0.0.1:8501/console"
python -m app.server.main

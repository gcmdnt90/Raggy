#!/bin/bash
# Raggy — Start script (Linux/Mac)

echo "🚀 Starting Raggy..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

cd "$ROOT"

# Create venv if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# First run — setup wizard
if [ ! -d "knowledge_base/chroma_db" ]; then
    echo "First run: starting setup wizard..."
    python scripts/setup_wizard.py
fi

echo "🌐 Starting Raggy at http://localhost:8501"
python -m streamlit run app/main.py

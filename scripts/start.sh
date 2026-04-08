#!/bin/bash
echo "🚀 Avvio EcoMeter..."
cd "$(dirname "$0")/.."

# Verifica Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 non trovato"
    exit 1
fi

VENV_PYTHON="venv/bin/python"

# Crea venv locale se non esiste
if [ ! -d "venv" ]; then
    echo "📦 Creazione ambiente virtuale locale..."
    python3 -m venv venv
    echo "📦 Installazione dipendenze nel venv locale..."
    venv/bin/python -m pip install --upgrade pip -q
    venv/bin/python -m pip install -r requirements.txt
fi

# Verifica KB
if [ ! -d "knowledge_base/chroma_db" ]; then
    echo "📚 Prima esecuzione: avvio setup wizard..."
    "$VENV_PYTHON" scripts/setup_wizard.py
fi

# Avvia con il Python del venv
echo "🌐 Avvio EcoMeter su http://localhost:8501"
"$VENV_PYTHON" -m streamlit run app/main.py

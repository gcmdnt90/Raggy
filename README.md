# Raggy - RAG-Powered Knowledge Assistant

A modular, self-hosted **Retrieval-Augmented Generation** chatbot that lets you build a custom knowledge base and query it using LLMs, locally with Ollama or via cloud APIs (Anthropic, OpenAI, Google).

## Features

- **RAG Chatbot** - Ask questions and get answers grounded in your documents.
- **Knowledge Base Manager** - Upload, organize, and index `.md`, `.txt`, `.pdf`, `.docx`, and `.xlsx` files.
- **Safety guards** - Input sanitization, prompt-injection spotlighting, document validation, and daily token budgets.
- **Multi-provider LLM** - Supports Ollama (local), Anthropic (Claude), OpenAI (GPT), and Google (Gemini).
- **Automatic Ollama Setup** - Detects your hardware, recommends models, and installs Ollama automatically.
- **Admin Panel** - Manage prompts, KB, settings, and usage logs.
- **Multilingual UI** - English (default) and Italian, switchable in Settings.
- **Persistent Config** - Settings saved to `.env`, surviving restarts.

## Quick Start

### Windows

```bat
start.bat
```

This will:

1. Create a Python virtual environment.
2. Install dependencies.
3. Run the setup wizard on first launch.
4. Open Raggy in your browser at `http://localhost:8501`.

### Manual

```bash
python -m venv venv
venv\Scripts\activate
source venv/bin/activate
pip install -r requirements.txt
streamlit run app/main.py
```

### Admin Panel

```bat
admin.bat
```

Or:

```bash
streamlit run app/admin.py --server.address 127.0.0.1 --server.port 8502
```

## Configuration

Copy `.env.example` to `.env` and set the provider values you need. `MAX_TOKENS` defaults to `1500` and is capped at `4000`; `DAILY_TOKEN_BUDGET` defaults to `200000`.

## CLI

```bash
python -m scripts.manage status
python -m scripts.manage reindex
python -m scripts.manage provider list
python -m scripts.manage provider set X
python -m scripts.manage ollama list
python -m scripts.manage ollama pull X
python -m scripts.manage ollama recommend
python -m scripts.manage start
python -m scripts.manage start --admin
```

## License

Apache License 2.0

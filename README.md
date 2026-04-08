# Raggy — RAG-Powered Knowledge Assistant

A modular, self-hosted **Retrieval-Augmented Generation** chatbot that lets you build a custom knowledge base and query it using LLMs — locally with Ollama or via cloud APIs (Anthropic, OpenAI, Google).

## Features

- 🧠 **RAG Chatbot** — Ask questions and get answers grounded in your documents
- 📚 **Knowledge Base Manager** — Upload, organize, and index `.md`, `.txt`, `.pdf` files
- 🔌 **Multi-provider LLM** — Supports Ollama (local), Anthropic (Claude), OpenAI (GPT), Google (Gemini)
- 🤖 **Automatic Ollama Setup** — Detects your hardware, recommends models, installs Ollama automatically
- 🛡️ **Admin Panel** — Manage prompts, KB, settings, and view usage logs
- 🌐 **Multilingual UI** — English (default) and Italian, switchable in Settings
- 💾 **Persistent Config** — Settings saved to `.env`, survives restarts

## Quick Start

### Windows
```
start.bat
```
This will:
1. Create a Python virtual environment
2. Install dependencies
3. Run the setup wizard (first time only)
4. Open Raggy in your browser at `http://localhost:8501`

### Manual
```bash
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
streamlit run app/main.py
```

### Admin Panel
```
admin.bat
```
Or: `streamlit run app/admin.py --server.port 8502`

## Project Structure

```
Raggy/
├── app/
│   ├── main.py              # Streamlit user app
│   ├── admin.py             # Streamlit admin panel
│   ├── config.py            # Pydantic settings from .env
│   ├── i18n.py              # Internationalization (EN/IT)
│   ├── gui/
│   │   ├── components.py    # Shared UI components
│   │   ├── chat.py          # Chatbot page
│   │   ├── settings.py      # Settings page
│   │   └── admin_panel.py   # Admin sections
│   ├── llm/
│   │   ├── base.py          # LLM abstractions
│   │   ├── router.py        # Provider routing
│   │   ├── ollama_setup.py  # Auto-install & model recommender
│   │   ├── providers/       # Anthropic, OpenAI, Google, Ollama
│   │   └── prompts/         # System prompt management
│   ├── rag/
│   │   ├── pipeline.py      # RAG orchestration
│   │   ├── retriever.py     # ChromaDB retriever
│   │   ├── embeddings.py    # Embedding management
│   │   └── memory.py        # Conversation memory
│   ├── parsers/
│   │   └── documents.py     # Generic document parser
│   └── utils/
│       ├── logger.py        # Interaction logging
│       └── logging_config.py
├── knowledge_base/           # Your documents go here
├── scripts/
│   ├── setup_wizard.py      # Guided first-run setup
│   ├── ingest_kb.py         # KB indexing script
│   └── manage.py            # CLI management tool
├── start.bat                 # Windows launcher
├── admin.bat                 # Windows admin launcher
├── requirements.txt
└── .env                      # Configuration (auto-generated)
```

## CLI

```bash
python -m scripts.manage status           # System status
python -m scripts.manage reindex          # Re-index KB
python -m scripts.manage provider list    # List providers
python -m scripts.manage provider set X   # Switch provider
python -m scripts.manage ollama list      # List Ollama models
python -m scripts.manage ollama pull X    # Download model
python -m scripts.manage ollama recommend # Get model recommendations
python -m scripts.manage start            # Start Raggy
python -m scripts.manage start --admin    # Start admin panel
```

## License

Apache License 2.0

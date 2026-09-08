#!/usr/bin/env python3
"""
Raggy Management CLI — Quick commands for management.

Usage:
    python -m scripts.manage status          # Show system status
    python -m scripts.manage reindex         # Re-index Knowledge Base
    python -m scripts.manage provider list   # List available providers
    python -m scripts.manage provider set X  # Change provider
    python -m scripts.manage prompt show     # Show current prompts
    python -m scripts.manage ollama pull X   # Download Ollama model
    python -m scripts.manage ollama list     # List installed Ollama models
    python -m scripts.manage start           # Start Raggy
    python -m scripts.manage start --admin   # Start admin panel
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Venv bootstrap ──────────────────────────────────────────────────────────
def _ensure_venv():
    if sys.prefix != sys.base_prefix:
        return
    venv_python = PROJECT_ROOT / "venv" / (
        "Scripts" if os.name == "nt" else "bin"
    ) / ("python.exe" if os.name == "nt" else "python")
    if venv_python.exists():
        os.execv(str(venv_python), [str(venv_python)] + sys.argv)
    else:
        print("⚠️  No active virtual environment and 'venv/' not found.")
        print("   Run start.bat (Windows) first.")
        sys.exit(1)

_ensure_venv()

import argparse   # noqa: E402
import subprocess # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT))


def cmd_status():
    """Show full system status."""
    from app.config import get_settings

    settings = get_settings()

    print("─── Raggy Status ───")
    print(f"  LLM Provider:    {settings.llm_provider}")
    print(f"  Model:           {settings.llm_model}")

    # KB documents
    kb_root = PROJECT_ROOT / "knowledge_base"
    from app.parsers.documents import SUPPORTED_EXTENSIONS
    all_files = [
        path for path in kb_root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    kb_docs = [f for f in all_files if "chroma_db" not in str(f) and f.name != "README.md"]
    print(f"  KB documents:    {len(kb_docs)}")

    # ChromaDB
    chroma_dir = kb_root / "chroma_db"
    if chroma_dir.exists():
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(chroma_dir))
            collection = client.get_collection("raggy_kb")
            count = collection.count()
            print(f"  KB chunks:       {count}")
            print(f"  ChromaDB:        ✅ OK")
        except Exception as e:
            print(f"  ChromaDB:        ⚠️  Error: {e}")
    else:
        print(f"  ChromaDB:        ❌ Not found (run 'reindex')")

    # Ollama
    try:
        import requests
        resp = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=3)
        if resp.ok:
            models = resp.json().get("models", [])
            print(f"  Ollama:          ✅ Active ({len(models)} models)")
        else:
            print(f"  Ollama:          ⚠️  Unexpected response")
    except Exception:
        print(f"  Ollama:          ⚠️  Unreachable")


def cmd_reindex():
    """Re-index the Knowledge Base."""
    print("📚 Re-indexing...")
    from scripts.ingest_kb import main as ingest_main
    ingest_main(rebuild=True)
    print("✅ Re-indexing complete!")


def cmd_provider(action: str, value: str = None):
    """Manage LLM providers."""
    if action == "list":
        print("Available providers:")
        print("  - anthropic  (Claude)")
        print("  - openai     (GPT-4o)")
        print("  - google     (Gemini)")
        print("  - ollama     (Local)")

    elif action == "set":
        if not value:
            print("❌ Specify provider: python -m scripts.manage provider set <name>")
            return
        valid = ["anthropic", "openai", "google", "ollama"]
        if value not in valid:
            print(f"❌ Invalid provider. Options: {', '.join(valid)}")
            return
        from app.config import save_settings_to_env
        save_settings_to_env({"llm_provider": value})
        print(f"✅ Provider set: {value}")


def cmd_prompt(action: str):
    """Manage system prompts."""
    if action == "show":
        prompts_dir = PROJECT_ROOT / "knowledge_base" / "prompts"
        if not prompts_dir.exists():
            print("❌ Prompts directory not found")
            return
        for yaml_file in sorted(prompts_dir.glob("*.yaml")):
            print(f"\n─── {yaml_file.stem} ───")
            content = yaml_file.read_text(encoding="utf-8")
            lines = content.splitlines()
            for line in lines[:10]:
                print(f"  {line}")
            if len(lines) > 10:
                print(f"  ... ({len(lines) - 10} lines remaining)")

    elif action == "edit":
        prompts_dir = PROJECT_ROOT / "knowledge_base" / "prompts"
        print(f"Prompt files are in: {prompts_dir}")
        print("Edit the YAML files with a text editor.")
        print("Changes take effect on next startup.")


def cmd_ollama(action: str, model: str = None):
    """Manage Ollama."""
    from app.config import get_settings
    settings = get_settings()
    base_url = settings.ollama_base_url

    if action == "list":
        try:
            import requests
            resp = requests.get(f"{base_url}/api/tags", timeout=5)
            if resp.ok:
                models = resp.json().get("models", [])
                if models:
                    print("Installed Ollama models:")
                    for m in models:
                        size_gb = m.get("size", 0) / (1024**3)
                        print(f"  - {m['name']} ({size_gb:.1f} GB)")
                else:
                    print("No models installed.")
            else:
                print("⚠️  Unexpected response from Ollama")
        except Exception:
            print("❌ Ollama unreachable")

    elif action == "pull":
        if not model:
            print("❌ Specify model: python -m scripts.manage ollama pull <name>")
            return
        print(f"⬇️  Downloading {model}...")
        try:
            subprocess.run(["ollama", "pull", model], check=True)
            print(f"✅ {model} downloaded!")
        except FileNotFoundError:
            print("❌ Ollama not found. Install from https://ollama.com")
        except subprocess.CalledProcessError:
            print(f"❌ Error downloading {model}")

    elif action == "recommend":
        from app.llm.ollama_setup import get_system_info, recommend_models
        info = get_system_info()
        print(f"System: {info['ram_gb']:.1f} GB RAM, GPU: {info.get('gpu_name', 'N/A')}")
        print()
        recommended = recommend_models(info)
        print("Recommended models:")
        for m in recommended:
            print(f"  - {m['name']} — {m['description']}")


def cmd_start(admin: bool = False):
    """Start Streamlit."""
    entry = "app/admin.py" if admin else "app/main.py"
    print(f"🚀 Starting Raggy ({'Admin' if admin else 'User'})...")
    args = [sys.executable, "-m", "app.server.main"]
    if admin:
        args.extend(["--server.address", "127.0.0.1", "--server.port", "8502"])
    subprocess.run(args)


def main():
    parser = argparse.ArgumentParser(
        description="Raggy Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="Show system status")
    subparsers.add_parser("reindex", help="Re-index Knowledge Base")

    provider_parser = subparsers.add_parser("provider", help="Manage LLM providers")
    provider_parser.add_argument("action", choices=["list", "set"])
    provider_parser.add_argument("value", nargs="?")

    prompt_parser = subparsers.add_parser("prompt", help="Manage prompts")
    prompt_parser.add_argument("action", choices=["show", "edit"])

    ollama_parser = subparsers.add_parser("ollama", help="Manage Ollama")
    ollama_parser.add_argument("action", choices=["pull", "list", "recommend"])
    ollama_parser.add_argument("model", nargs="?")

    start_parser = subparsers.add_parser("start", help="Start Raggy")
    start_parser.add_argument("--admin", action="store_true", help="Start admin panel")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "status":
        cmd_status()
    elif args.command == "reindex":
        cmd_reindex()
    elif args.command == "provider":
        cmd_provider(args.action, getattr(args, "value", None))
    elif args.command == "prompt":
        cmd_prompt(args.action)
    elif args.command == "ollama":
        cmd_ollama(args.action, getattr(args, "model", None))
    elif args.command == "start":
        cmd_start(admin=args.admin)


if __name__ == "__main__":
    main()

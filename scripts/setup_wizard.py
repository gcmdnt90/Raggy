#!/usr/bin/env python3
"""Raggy Setup Wizard — Guided first-run configuration."""

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

import subprocess  # noqa: E402
import shutil      # noqa: E402
import getpass     # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT))


def print_header():
    print("╔══════════════════════════════════════════════════╗")
    print("║     Raggy — Setup Wizard v0.1.1                 ║")
    print("║     RAG-Powered Knowledge Assistant              ║")
    print("╚══════════════════════════════════════════════════╝")
    print()
    print("Welcome! This wizard will configure Raggy on your PC.")
    print()


def print_success():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  ✅ Setup complete!                              ║")
    print("║                                                  ║")
    print("║  To start Raggy:                                 ║")
    print("║    start.bat               (Windows)             ║")
    print("║    streamlit run app/main.py                     ║")
    print("║                                                  ║")
    print("║  For the admin panel:                            ║")
    print("║    admin.bat               (Windows)             ║")
    print("║    streamlit run app/admin.py                    ║")
    print("║      --server.address 127.0.0.1 --server.port 8502 ║")
    print("║                                                  ║")
    print("║  For CLI commands:                               ║")
    print("║    python -m scripts.manage --help               ║")
    print("╚══════════════════════════════════════════════════╝")


def step_check_dependencies() -> dict:
    """Step 1: Check Python, pip, dependencies, Ollama."""
    print("─── Step 1/5: Check Dependencies ──────────────────")

    info = {}

    v = sys.version.split()[0]
    print(f"  ✅ Python {v}")
    info["python"] = v

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True, text=True,
        )
        pip_ver = result.stdout.split()[1] if result.returncode == 0 else "?"
        print(f"  ✅ pip {pip_ver}")
    except Exception:
        print("  ⚠️  pip not found")

    req_file = PROJECT_ROOT / "requirements.txt"
    if req_file.exists():
        print("  ✅ requirements.txt found")
    else:
        print("  ❌ requirements.txt not found!")

    # Ollama
    from app.llm.ollama_setup import is_ollama_installed, get_system_info, recommend_models

    if is_ollama_installed():
        print("  ✅ Ollama found")
        info["ollama"] = True
    else:
        print("  ⚠️  Ollama not found (optional for local use)")
        info["ollama"] = False
        print()
        install = input("  Would you like to install Ollama automatically? [y/N]: ").strip().lower()
        if install == "y":
            from app.llm.ollama_setup import install_ollama
            success, msg = install_ollama()
            if success:
                print(f"  ✅ {msg}")
                info["ollama"] = True
            else:
                print(f"  ⚠️  {msg}")

    # System info + model recommendations
    if info.get("ollama"):
        print()
        print("  📊 System Information:")
        sysinfo = get_system_info()
        print(f"     RAM: {sysinfo['ram_gb']:.1f} GB")
        if sysinfo.get("gpu_name"):
            print(f"     GPU: {sysinfo['gpu_name']} ({sysinfo.get('vram_gb', 0):.1f} GB VRAM)")
        else:
            print("     GPU: Not detected (CPU-only mode)")

        recommended = recommend_models(sysinfo)
        print()
        print("  🤖 Recommended models for your system:")
        for i, m in enumerate(recommended, 1):
            print(f"     [{i}] {m['name']} — {m['description']}")
        info["recommended_models"] = recommended
        info["sysinfo"] = sysinfo

    print()
    return info


def step_configure_llm(deps: dict) -> dict:
    """Step 2: Choose and configure LLM provider."""
    print("─── Step 2/5: LLM Configuration ────────────────────")
    print("How do you want to use Raggy?")
    print()
    print("  [1] With cloud API (Anthropic/OpenAI/Google)")
    print("  [2] With Ollama (local)")
    print("  [3] Both")
    print()

    choice = _input_choice("Choice [1/2/3]: ", ["1", "2", "3"])
    config = {}

    if choice in ("1", "3"):
        print()
        print("Which provider do you prefer?")
        print("  [1] Anthropic (Claude) — Recommended")
        print("  [2] OpenAI (GPT-4o)")
        print("  [3] Google (Gemini)")
        print()

        provider_choice = _input_choice("Choice [1/2/3]: ", ["1", "2", "3"])
        provider_map = {"1": "anthropic", "2": "openai", "3": "google"}
        key_env_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "google": "GOOGLE_API_KEY",
        }

        provider = provider_map[provider_choice]
        config["provider"] = provider

        api_key = input(f"Enter your {provider.title()} API key: ").strip()
        config["api_key"] = api_key
        config["key_env"] = key_env_map[provider]

        print("  🔌 Testing connection...", end=" ", flush=True)
        if _test_api_key(provider, api_key):
            print("✅ Works!")
        else:
            print("⚠️  Could not verify now, continuing.")

    if choice in ("2", "3"):
        config.setdefault("provider", "ollama")

        # Offer to download recommended model
        recommended = deps.get("recommended_models", [])
        if recommended:
            print()
            print("  Would you like to download a recommended model?")
            for i, m in enumerate(recommended, 1):
                print(f"    [{i}] {m['name']} — {m['description']}")
            print(f"    [0] Skip")
            print()

            valid = [str(i) for i in range(len(recommended) + 1)]
            dl_choice = _input_choice("Choice: ", valid)
            if dl_choice != "0":
                model = recommended[int(dl_choice) - 1]["name"]
                config["model"] = model
                print(f"  ⬇️  Downloading {model}...")
                try:
                    subprocess.run(["ollama", "pull", model], check=True)
                    print(f"  ✅ {model} downloaded!")
                except Exception as e:
                    print(f"  ⚠️  Download failed: {e}")
        else:
            print()
            print("  Checking Ollama connection...", end=" ", flush=True)
            try:
                import requests
                resp = requests.get("http://localhost:11434/api/tags", timeout=5)
                if resp.ok:
                    models = [m["name"] for m in resp.json().get("models", [])]
                    print(f"✅ {len(models)} models found")
                    if models:
                        print(f"  Models: {', '.join(models[:5])}")
                else:
                    print("⚠️  Ollama active but unexpected response")
            except Exception:
                print("⚠️  Ollama not reachable on localhost:11434")

    print()
    return config


def _test_api_key(provider: str, api_key: str) -> bool:
    """Quick connection test."""
    try:
        if provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            client.messages.create(
                model="claude-sonnet-4-20250514", max_tokens=10,
                messages=[{"role": "user", "content": "test"}],
            )
            return True
        elif provider == "openai":
            import openai
            client = openai.OpenAI(api_key=api_key)
            client.chat.completions.create(
                model="gpt-4o-mini", max_tokens=10,
                messages=[{"role": "user", "content": "test"}],
            )
            return True
        elif provider == "google":
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            model.generate_content("test")
            return True
    except Exception:
        return False
    return False


def step_configure_hf_token() -> str:
    """Step 3b: Hugging Face token (optional)."""
    print("─── Step 3b/5: Hugging Face Token (optional) ──────")
    print("Raggy uses a local embedding model (sentence-transformers).")
    print("Download is free and public, but without an HF token you have")
    print("reduced rate limits. If you have an account on huggingface.co")
    print("you can enter your token.")
    print()
    print("Leave empty to skip (it works either way).")
    print()

    token = input("HF Token (optional, starts with 'hf_'): ").strip()
    if token:
        if not token.startswith("hf_"):
            print("  ⚠️  Token doesn't look valid (should start with 'hf_'). Ignored.")
            return ""
        print("  ✅ HF token set.")
    else:
        print("  ℹ️  No token — public downloads with standard rate limits.")
    print()
    return token


def step_set_admin_password() -> str:
    """Step 4: Set admin password."""
    print("─── Step 4/5: Admin Password ───────────────────────")
    print("Set a password for the admin panel.")
    print("(It will be saved to the local .env file)")
    print()

    while True:
        password = getpass.getpass("Password: ")
        if len(password) < 4:
            print("  ❌ Password must be at least 4 characters.")
            continue
        confirm = getpass.getpass("Confirm: ")
        if password != confirm:
            print("  ❌ Passwords don't match! Try again.")
            continue
        break

    print("  ✅ Password set")
    print()
    return password


def step_test():
    """Step 5: Final test."""
    print("─── Step 5/5: Final Test ──────────────────────────")
    print("  🧪 Verifying module loading...", end=" ", flush=True)

    try:
        from app.config import get_settings
        settings = get_settings()
        print(f"✅ Config loaded (provider: {settings.llm_provider})")
    except Exception as e:
        print(f"⚠️  {e}")

    print()


def _save_env(config: dict, password: str, hf_token: str = ""):
    """Save configuration to .env file."""
    from app.config import save_settings_to_env

    updates = {
        "admin_password": password,
        "max_tokens": 1500,
        "daily_token_budget": 200000,
    }
    if config.get("provider"):
        updates["llm_provider"] = config["provider"]
    if config.get("model"):
        updates["llm_model"] = config["model"]
    if config.get("key_env") and config.get("api_key"):
        # Map key_env to field name
        env_to_field = {
            "ANTHROPIC_API_KEY": "anthropic_api_key",
            "OPENAI_API_KEY": "openai_api_key",
            "GOOGLE_API_KEY": "google_api_key",
        }
        field = env_to_field.get(config["key_env"])
        if field:
            updates[field] = config["api_key"]
    if hf_token:
        updates["hf_token"] = hf_token

    save_settings_to_env(updates)
    print("  ✅ Configuration saved to .env")


def _input_choice(prompt: str, valid: list[str]) -> str:
    """Input with validation."""
    while True:
        val = input(prompt).strip()
        if val in valid:
            return val
        print(f"  Invalid choice. Options: {', '.join(valid)}")


def main():
    print_header()

    deps = step_check_dependencies()
    config = step_configure_llm(deps)
    hf_token = step_configure_hf_token()
    password = step_set_admin_password()
    _save_env(config, password, hf_token)
    step_test()

    print_success()


if __name__ == "__main__":
    main()

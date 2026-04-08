"""Ollama auto-installer, system profiler, and model recommender for Raggy."""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def is_ollama_installed() -> bool:
    """Check if Ollama is available in PATH or common install locations."""
    if shutil.which("ollama"):
        return True
    # Windows: check common install path
    if os.name == "nt":
        common_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Ollama\ollama.exe"),
        ]
        return any(os.path.isfile(p) for p in common_paths)
    return False


def is_ollama_running(base_url: str = "http://localhost:11434") -> bool:
    """Check if Ollama server is responding."""
    try:
        import requests
        resp = requests.get(f"{base_url}/api/tags", timeout=3)
        return resp.ok
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------

def install_ollama() -> tuple[bool, str]:
    """Download and install Ollama. Returns (success, message).

    Currently supports Windows (MSI) and Linux (curl script).
    """
    system = platform.system().lower()

    try:
        if system == "windows":
            return _install_ollama_windows()
        elif system == "linux":
            return _install_ollama_linux()
        elif system == "darwin":
            return False, "On macOS, install Ollama from https://ollama.com/download or via `brew install ollama`."
        else:
            return False, f"Unsupported OS: {system}. Install from https://ollama.com/download"
    except Exception as e:
        logger.exception("Ollama installation failed")
        return False, str(e)


def _install_ollama_windows() -> tuple[bool, str]:
    """Download and run the Ollama Windows installer."""
    import tempfile
    import urllib.request
    from pathlib import Path

    url = "https://ollama.com/download/OllamaSetup.exe"
    tmp_dir = Path(tempfile.gettempdir())
    installer = tmp_dir / "OllamaSetup.exe"

    logger.info("Downloading Ollama installer from %s", url)
    urllib.request.urlretrieve(url, str(installer))

    logger.info("Running Ollama installer: %s", installer)
    result = subprocess.run(
        [str(installer), "/VERYSILENT", "/NORESTART"],
        timeout=300,
        capture_output=True, text=True,
    )

    if result.returncode == 0:
        return True, "Ollama installed successfully."
    else:
        return False, f"Installer exited with code {result.returncode}: {result.stderr[:200]}"


def _install_ollama_linux() -> tuple[bool, str]:
    """Install Ollama via the official curl script."""
    result = subprocess.run(
        ["bash", "-c", "curl -fsSL https://ollama.ai/install.sh | sh"],
        timeout=300,
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return True, "Ollama installed successfully."
    return False, f"Install script failed: {result.stderr[:200]}"


# ---------------------------------------------------------------------------
# System profiling
# ---------------------------------------------------------------------------

def get_system_info() -> dict[str, Any]:
    """Gather system information for model recommendations.

    Returns a dict with keys: ram_gb, cpu_cores, gpu_name, vram_gb, os.
    """
    info: dict[str, Any] = {
        "os": platform.system(),
        "ram_gb": 0.0,
        "cpu_cores": os.cpu_count() or 1,
        "gpu_name": None,
        "vram_gb": 0.0,
    }

    # RAM
    try:
        import psutil
        info["ram_gb"] = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    except ImportError:
        # Fallback: platform-specific
        if os.name == "nt":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                c_ulong = ctypes.c_ulonglong
                mem = c_ulong()
                kernel32.GetPhysicallyInstalledSystemMemory(ctypes.byref(mem))
                info["ram_gb"] = round(mem.value / (1024 * 1024), 1)
            except Exception:
                pass
        else:
            try:
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            kb = int(line.split()[1])
                            info["ram_gb"] = round(kb / (1024 * 1024), 1)
                            break
            except Exception:
                pass

    # GPU detection
    info.update(_detect_gpu())

    return info


def _detect_gpu() -> dict[str, Any]:
    """Detect GPU name and VRAM."""
    result: dict[str, Any] = {"gpu_name": None, "vram_gb": 0.0}

    # Try nvidia-smi first
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            parts = out.stdout.strip().split(",")
            result["gpu_name"] = parts[0].strip()
            result["vram_gb"] = round(float(parts[1].strip()) / 1024, 1)
            return result
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Windows fallback: WMI
    if os.name == "nt":
        try:
            out = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "Name,AdapterRAM", "/format:csv"],
                capture_output=True, text=True, timeout=10,
            )
            if out.returncode == 0:
                for line in out.stdout.strip().splitlines():
                    parts = line.strip().split(",")
                    if len(parts) >= 3 and parts[1].strip().isdigit():
                        adapter_ram = int(parts[1])
                        if adapter_ram > 0:
                            result["gpu_name"] = parts[2].strip()
                            result["vram_gb"] = round(adapter_ram / (1024 ** 3), 1)
                            return result
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return result


# ---------------------------------------------------------------------------
# Model recommendation
# ---------------------------------------------------------------------------

# Model tiers ordered by resource requirement
_MODEL_TIERS: list[dict[str, Any]] = [
    # Tier 1: Ultra-light (≤4 GB RAM)
    {
        "min_ram_gb": 0, "max_ram_gb": 4, "min_vram_gb": 0,
        "models": [
            {"name": "gemma3:1b", "description": "Google Gemma 3 1B — minimal, fast, good for basic tasks"},
            {"name": "qwen3:0.6b", "description": "Qwen 3 0.6B — ultra-light, rapid responses"},
        ],
    },
    # Tier 2: Light (4–8 GB RAM)
    {
        "min_ram_gb": 4, "max_ram_gb": 8, "min_vram_gb": 0,
        "models": [
            {"name": "gemma3:4b", "description": "Google Gemma 3 4B — great quality/speed balance"},
            {"name": "qwen3:4b", "description": "Qwen 3 4B — strong multilingual reasoning"},
            {"name": "phi4-mini", "description": "Microsoft Phi-4 Mini — compact but capable"},
        ],
    },
    # Tier 3: Medium (8–16 GB RAM or 4+ GB VRAM)
    {
        "min_ram_gb": 8, "max_ram_gb": 16, "min_vram_gb": 4,
        "models": [
            {"name": "gemma3:12b", "description": "Google Gemma 3 12B — high quality, good for RAG"},
            {"name": "mistral-nemo", "description": "Mistral Nemo 12B — excellent reasoning"},
            {"name": "qwen3:8b", "description": "Qwen 3 8B — strong multilingual performance"},
        ],
    },
    # Tier 4: High (16+ GB RAM or 8+ GB VRAM)
    {
        "min_ram_gb": 16, "max_ram_gb": 9999, "min_vram_gb": 8,
        "models": [
            {"name": "gemma3:27b", "description": "Google Gemma 3 27B — near-frontier quality"},
            {"name": "qwen3:14b", "description": "Qwen 3 14B — excellent for complex reasoning"},
            {"name": "mistral-small", "description": "Mistral Small 22B — high quality, longer context"},
        ],
    },
]


def recommend_models(system_info: dict[str, Any]) -> list[dict[str, str]]:
    """Return recommended models based on system capabilities.

    Returns a list of {"name": ..., "description": ...} dicts.
    """
    ram = system_info.get("ram_gb", 0)
    vram = system_info.get("vram_gb", 0)

    # Find the highest tier the system can run
    best_tier = _MODEL_TIERS[0]  # fallback to lightest
    for tier in _MODEL_TIERS:
        if ram >= tier["min_ram_gb"]:
            # Check if system meets either RAM or VRAM requirements
            if ram >= tier["min_ram_gb"] or vram >= tier["min_vram_gb"]:
                best_tier = tier

    return best_tier["models"]

"""Raggy i18n — Lightweight internationalization with English/Italian support."""

from __future__ import annotations

import streamlit as st

SUPPORTED_LANGUAGES = {"en": "English", "it": "Italiano"}
DEFAULT_LANGUAGE = "en"

# ---------------------------------------------------------------------------
# Translation dictionaries
# ---------------------------------------------------------------------------

_TRANSLATIONS: dict[str, dict[str, str]] = {
    # ── Navigation & global ───────────────────────────────────────────────
    "app_title": {"en": "Raggy", "it": "Raggy"},
    "app_subtitle": {"en": "RAG-Powered Knowledge Assistant", "it": "Assistente basato su RAG"},
    "nav_chat": {"en": "Chat", "it": "Chat"},
    "nav_settings": {"en": "Settings", "it": "Impostazioni"},
    "nav_navigation": {"en": "Navigation", "it": "Navigazione"},
    "version_label": {"en": "Raggy v1.0", "it": "Raggy v1.0"},
    "llm_not_configured": {"en": "LLM not configured", "it": "LLM non configurato"},
    "llm_go_settings": {
        "en": "Go to Settings to configure your LLM provider.",
        "it": "Vai su Impostazioni per configurare il provider LLM.",
    },

    # ── Chat ──────────────────────────────────────────────────────────────
    "chat_title": {"en": "Knowledge Assistant", "it": "Assistente Knowledge Base"},
    "chat_subtitle": {
        "en": "Ask questions about your knowledge base documents.",
        "it": "Fai domande sui documenti nella Knowledge Base.",
    },
    "chat_placeholder": {"en": "Type your question...", "it": "Scrivi la tua domanda..."},
    "chat_suggestions_title": {"en": "Here are some ideas to get started:", "it": "Ecco alcuni spunti per iniziare:"},
    "chat_sugg_1": {"en": "What topics are covered in the knowledge base?", "it": "Quali argomenti sono trattati nella Knowledge Base?"},
    "chat_sugg_2": {"en": "Summarize the key points from the documents.", "it": "Riassumi i punti chiave dai documenti."},
    "chat_sugg_3": {"en": "What best practices are mentioned?", "it": "Quali best practice sono menzionate?"},
    "chat_sugg_4": {"en": "Are there any regulations or standards referenced?", "it": "Ci sono normative o standard di riferimento?"},
    "chat_configure_llm": {
        "en": "Configure the LLM provider in Settings to use the chatbot.",
        "it": "Configura il provider LLM nella pagina Impostazioni per utilizzare il chatbot.",
    },
    "chat_error": {"en": "Error", "it": "Errore"},
    "chat_configure_msg": {
        "en": "Please configure the LLM provider in Settings.",
        "it": "Per favore, configura il provider LLM nella pagina Impostazioni.",
    },

    # ── Settings ──────────────────────────────────────────────────────────
    "settings_title": {"en": "Settings", "it": "Impostazioni"},
    "settings_provider": {"en": "LLM Provider", "it": "Provider LLM"},
    "settings_select_provider": {"en": "Select provider", "it": "Seleziona provider"},
    "settings_ollama_url": {"en": "Ollama URL", "it": "Ollama URL"},
    "settings_ollama_url_help": {
        "en": "Address of the Ollama server. Default: http://localhost:11434",
        "it": "Indirizzo del server Ollama. Default: http://localhost:11434",
    },
    "settings_ollama_connected": {"en": "Ollama connected", "it": "Ollama connesso"},
    "settings_ollama_models_available": {"en": "models available", "it": "modelli disponibili"},
    "settings_ollama_unreachable": {
        "en": "Ollama unreachable or no models installed.\nStart Ollama with `ollama serve` and download a model with `ollama pull <name>`.",
        "it": "Ollama non raggiungibile o nessun modello installato.\nAvvia Ollama con `ollama serve` e scarica un modello con `ollama pull <nome>`.",
    },
    "settings_ollama_model": {"en": "Ollama Model", "it": "Modello Ollama"},
    "settings_ollama_model_manual": {"en": "Ollama Model (enter manually)", "it": "Modello Ollama (inserisci manualmente)"},
    "settings_ollama_model_hint": {"en": "e.g. gemma3:4b, qwen3:4b, mistral-nemo", "it": "Es: gemma3:4b, qwen3:4b, mistral-nemo"},
    "settings_timeout": {"en": "Generation timeout (seconds)", "it": "Timeout generazione (secondi)"},
    "settings_timeout_help": {
        "en": "Local models can be slow — increase if generation cuts off.",
        "it": "Modelli locali lenti richiedono timeout più alti. Aumenta se la generazione si interrompe.",
    },
    "settings_api_key": {"en": "API Key", "it": "Chiave API"},
    "settings_api_key_help": {
        "en": "The key is saved to .env only when you press 'Save as Default'.",
        "it": "La chiave viene salvata in .env solo se premi 'Salva come Default'.",
    },
    "settings_model": {"en": "Model", "it": "Modello"},
    "settings_embedding_title": {"en": "Embedding Model (local)", "it": "Modello Embedding (locale)"},
    "settings_hf_token": {"en": "Hugging Face Token (optional)", "it": "Token Hugging Face (opzionale)"},
    "settings_hf_token_help": {
        "en": "HF token for authenticated downloads of the local embedding model. Without it, public downloads work but with lower rate limits.",
        "it": "Token HF per download autenticati del modello di embedding locale. Senza token funziona ugualmente ma con rate limit ridotti.",
    },
    "settings_gen_params": {"en": "Generation Parameters", "it": "Parametri Generazione"},
    "settings_temperature": {"en": "Temperature", "it": "Temperature"},
    "settings_temperature_help": {
        "en": "Lower = more deterministic. Higher = more creative.",
        "it": "Più basso = risposte più deterministiche. Più alto = più creative.",
    },
    "settings_max_tokens": {"en": "Max Tokens", "it": "Max Token"},
    "settings_test_connection": {"en": "🔌 Test Connection", "it": "🔌 Testa Connessione"},
    "settings_testing": {"en": "Testing...", "it": "Test in corso..."},
    "settings_connection_ok": {"en": "Connection successful!", "it": "Connessione riuscita!"},
    "settings_pipeline_ready": {"en": "RAG Pipeline ready!", "it": "Pipeline RAG pronta!"},
    "settings_connection_failed": {
        "en": "Connection failed. Check credentials and that the service is running.",
        "it": "Connessione fallita. Verifica le credenziali e che il servizio sia attivo.",
    },
    "settings_save": {"en": "💾 Save as Default", "it": "💾 Salva come Default"},
    "settings_save_help": {
        "en": "Writes settings to .env — they will be loaded on every startup",
        "it": "Scrive le impostazioni nel file .env — saranno caricate ad ogni avvio",
    },
    "settings_saved": {"en": "Settings saved to .env!", "it": "Impostazioni salvate in .env!"},
    "settings_save_error": {"en": "Error saving settings", "it": "Errore nel salvataggio"},
    "settings_system_status": {"en": "System Status", "it": "Stato Sistema"},
    "settings_active_provider": {"en": "Active provider", "it": "Provider attivo"},
    "settings_connected": {"en": "connected", "it": "connesso"},
    "settings_not_configured": {"en": "not configured", "it": "non configurato"},
    "settings_kb_chunks": {"en": "KB chunks", "it": "KB chunks"},
    "settings_kb_not_indexed": {"en": "not indexed", "it": "non indicizzata"},
    "settings_config_details": {"en": "Configuration details", "it": "Dettagli configurazione"},
    "settings_language_title": {"en": "Language / Lingua", "it": "Lingua / Language"},
    "settings_language_label": {"en": "Interface language", "it": "Lingua interfaccia"},

    # ── Ollama Setup ──────────────────────────────────────────────────────
    "ollama_setup_title": {"en": "Ollama Setup", "it": "Setup Ollama"},
    "ollama_not_installed": {
        "en": "Ollama is not installed on this system.",
        "it": "Ollama non è installato su questo sistema.",
    },
    "ollama_install_btn": {"en": "⬇️ Install Ollama", "it": "⬇️ Installa Ollama"},
    "ollama_installing": {"en": "Downloading and installing Ollama...", "it": "Download e installazione di Ollama..."},
    "ollama_install_ok": {"en": "Ollama installed successfully! Please restart the app.", "it": "Ollama installato con successo! Riavvia l'app."},
    "ollama_install_fail": {"en": "Ollama installation failed", "it": "Installazione di Ollama fallita"},
    "ollama_sysinfo_title": {"en": "System Information", "it": "Informazioni Sistema"},
    "ollama_recommend_title": {"en": "Recommended Models", "it": "Modelli Consigliati"},
    "ollama_pull_btn": {"en": "Download", "it": "Scarica"},
    "ollama_pulling": {"en": "Downloading model...", "it": "Download modello in corso..."},
    "ollama_pull_ok": {"en": "Model downloaded successfully!", "it": "Modello scaricato con successo!"},
    "ollama_pull_fail": {"en": "Failed to download model", "it": "Errore nel download del modello"},

    # ── Privacy ───────────────────────────────────────────────────────────
    "privacy_warning": {
        "en": "**Privacy Notice:** You are using a cloud provider. Data will be sent to the selected provider's servers. Use Ollama to keep everything local.",
        "it": "**Nota Privacy:** Stai usando un provider cloud. I dati verranno inviati ai server del provider selezionato. Per mantenere i dati completamente locali, usa Ollama.",
    },

    # ── Admin ─────────────────────────────────────────────────────────────
    "admin_title": {"en": "Raggy Admin", "it": "Raggy Admin"},
    "admin_login_title": {"en": "Raggy — Admin Panel", "it": "Raggy — Pannello Admin"},
    "admin_password": {"en": "Password", "it": "Password"},
    "admin_login": {"en": "Login", "it": "Accedi"},
    "admin_wrong_password": {"en": "Wrong password", "it": "Password errata"},
    "admin_logout": {"en": "Logout", "it": "Logout"},
    "admin_section_chatbot": {"en": "Admin Chat", "it": "Chatbot Admin"},
    "admin_section_prompts": {"en": "Prompts", "it": "Prompt"},
    "admin_section_kb": {"en": "Knowledge Base", "it": "Knowledge Base"},
    "admin_section_settings": {"en": "Settings", "it": "Impostazioni"},
    "admin_section_logs": {"en": "Logs", "it": "Log"},

    # ── Admin KB ──────────────────────────────────────────────────────────
    "kb_title": {"en": "Knowledge Base Manager", "it": "Gestione Knowledge Base"},
    "kb_docs_md": {"en": "MD Documents", "it": "Documenti MD"},
    "kb_chunks_indexed": {"en": "Chunks indexed", "it": "Chunks indicizzati"},
    "kb_files_in_kb": {"en": "Files in Knowledge Base:", "it": "File nella Knowledge Base:"},
    "kb_upload_title": {"en": "Upload documents to KB:", "it": "Carica documenti nella KB:"},
    "kb_upload_file": {"en": "Upload file", "it": "Carica file"},
    "kb_category": {"en": "Category", "it": "Categoria"},
    "kb_new_category": {"en": "New category name", "it": "Nome nuova categoria"},
    "kb_add_btn": {"en": "Add to KB", "it": "Aggiungi alla KB"},
    "kb_added": {"en": "added to", "it": "aggiunto a"},
    "kb_reindex_btn": {"en": "Re-index entire KB", "it": "Re-indicizza tutta la KB"},
    "kb_reindexing": {"en": "Re-indexing...", "it": "Re-indicizzazione in corso..."},
    "kb_reindexed": {"en": "Knowledge Base re-indexed!", "it": "Knowledge Base re-indicizzata!"},
    "kb_view": {"en": "View", "it": "Vedi"},
    "kb_edit": {"en": "Edit", "it": "Modifica"},
    "kb_delete_confirm": {"en": "Permanently delete", "it": "Eliminare definitivamente"},
    "kb_delete_yes": {"en": "Yes, delete", "it": "Sì, elimina"},
    "kb_cancel": {"en": "Cancel", "it": "Annulla"},
    "kb_save": {"en": "Save", "it": "Salva"},
    "kb_saved": {"en": "Saved.", "it": "Salvato."},
    "kb_deleted": {"en": "deleted.", "it": "eliminato."},
    "kb_close": {"en": "Close", "it": "Chiudi"},
    "kb_no_reindex_note": {"en": "Changes are not automatically re-indexed.", "it": "Le modifiche non vengono re-indicizzate automaticamente."},

    # ── Admin Prompts ─────────────────────────────────────────────────────
    "prompts_title": {"en": "System Prompt Editor", "it": "Editor System Prompt"},
    "prompts_type": {"en": "Prompt type", "it": "Tipo di prompt"},
    "prompts_chatbot": {"en": "General Chatbot", "it": "Chatbot Generale"},
    "prompts_admin": {"en": "Admin Chatbot", "it": "Admin Chatbot"},
    "prompts_textarea_help": {"en": "Edit the prompt and save. Changes are immediate.", "it": "Modifica il prompt e salva. Le modifiche sono immediate."},
    "prompts_save": {"en": "Save", "it": "Salva"},
    "prompts_saved": {"en": "Prompt saved!", "it": "Prompt salvato!"},
    "prompts_reset": {"en": "Reset to Default", "it": "Ripristina Default"},

    # ── Admin Logs ────────────────────────────────────────────────────────
    "logs_title": {"en": "Logs & Usage", "it": "Log e Utilizzo"},
    "logs_today": {"en": "Conversations today", "it": "Conversazioni oggi"},
    "logs_total": {"en": "Total reports", "it": "Report generati (totale)"},
    "logs_recent": {"en": "Recent interactions:", "it": "Ultime interazioni:"},
    "logs_none": {"en": "No logs available.", "it": "Nessun log disponibile."},

    # ── Setup Wizard ──────────────────────────────────────────────────────
    "wizard_title": {"en": "Raggy — Setup Wizard", "it": "Raggy — Setup Wizard"},
    "wizard_welcome": {"en": "Welcome! This wizard will configure Raggy on your PC.", "it": "Benvenuto! Questo wizard configurerà Raggy sul tuo PC."},
}


def t(key: str, **kwargs) -> str:
    """Return the translated string for *key* in the active language.

    Falls back to English if the key or language is missing.
    Supports ``{placeholder}`` formatting via **kwargs.
    """
    lang = get_language()
    entry = _TRANSLATIONS.get(key)
    if entry is None:
        return key  # missing key — return as-is for debugging
    text = entry.get(lang, entry.get("en", key))
    if kwargs:
        text = text.format(**kwargs)
    return text


def get_language() -> str:
    """Return the current UI language code (reads from session state)."""
    try:
        return st.session_state.get("ui_language", DEFAULT_LANGUAGE)
    except Exception:
        return DEFAULT_LANGUAGE


def set_language(lang: str) -> None:
    """Set the UI language (persists in session state)."""
    if lang in SUPPORTED_LANGUAGES:
        st.session_state["ui_language"] = lang

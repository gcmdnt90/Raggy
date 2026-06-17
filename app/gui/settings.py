"""Settings page — LLM provider config with .env persistence + Ollama setup."""

import logging

import streamlit as st

from app.config import get_settings, save_settings_to_env, CHROMA_PERSIST_DIR
from app.i18n import t, SUPPORTED_LANGUAGES, set_language, get_language

logger = logging.getLogger(__name__)

# Default timeout per provider (seconds)
_DEFAULT_TIMEOUT = {
    "anthropic": 120,
    "openai": 120,
    "google": 120,
    "ollama": 300,   # local models are slow — allow up to 5 min
}


def _init_router(provider: str, api_key: str = "", model: str = "",
                 base_url: str = "", timeout: int = 120,
                 temperature: float = 0.3, max_tokens: int = 1500):
    """Create an LLMRouter with the given parameters."""
    from app.llm.router import LLMRouter
    kwargs: dict = {"timeout": timeout, "temperature": temperature, "max_tokens": max_tokens}
    if model:
        kwargs["model"] = model
    if provider == "ollama":
        kwargs["base_url"] = base_url or "http://localhost:11434"
    elif api_key:
        kwargs["api_key"] = api_key
    logger.debug("Creating router: provider=%s model=%s timeout=%s", provider, model, timeout)
    return LLMRouter(provider=provider, **kwargs)


def _init_pipeline(router):
    """Initialize the RAG pipeline with the given router."""
    try:
        from app.rag.retriever import ChromaRetriever
        from app.rag.pipeline import RAGPipeline
        retriever = ChromaRetriever()
        retriever.embedding_manager.preload()
        pipeline = RAGPipeline(router=router, retriever=retriever)
        logger.info("RAG pipeline initialized with provider=%s", router.provider_name)
        return pipeline
    except Exception as e:
        logger.exception("Could not initialize RAG pipeline")
        st.warning(f"Knowledge Base not available: {e}")
        return None


def _get_ollama_models(base_url: str) -> list[str]:
    """Query Ollama for the list of models. Returns [] if unreachable."""
    try:
        import requests
        resp = requests.get(f"{base_url}/api/tags", timeout=3)
        if resp.ok:
            return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        pass
    return []


def _get_api_models(provider: str, api_key: str) -> tuple[list[str], bool]:
    """Return (models, live) for an API provider.

    Attempts a live query against the provider when an API key is present;
    falls back to the curated static list otherwise. ``live`` is True only when
    the list came from the provider's API.
    """
    from app.llm.providers import model_catalog

    if api_key:
        try:
            from app.llm.router import LLMRouter
            router = LLMRouter(provider, api_key=api_key, timeout=10)
            models = router.available_models()
            if models:
                return models, True
        except Exception:
            logger.debug("Live model fetch failed for %s", provider, exc_info=True)
    return model_catalog.fallback(provider), False


def _show_ollama_setup():
    """Show Ollama installation and model recommendation section."""
    from app.llm.ollama_setup import is_ollama_installed, install_ollama, get_system_info, recommend_models

    if not is_ollama_installed():
        st.warning(t("ollama_not_installed"))
        if st.button(t("ollama_install_btn"), type="primary"):
            with st.spinner(t("ollama_installing")):
                success, msg = install_ollama()
                if success:
                    st.success(t("ollama_install_ok"))
                else:
                    st.error(f"{t('ollama_install_fail')}: {msg}")
        return

    # System info + model recommendations
    with st.expander(t("ollama_sysinfo_title")):
        info = get_system_info()
        col1, col2, col3 = st.columns(3)
        col1.metric("RAM", f"{info['ram_gb']:.1f} GB")
        col2.metric("GPU", info.get("gpu_name", "N/A"))
        col3.metric("VRAM", f"{info.get('vram_gb', 0):.1f} GB" if info.get("vram_gb") else "N/A")

        st.divider()
        st.subheader(t("ollama_recommend_title"))
        recommended = recommend_models(info)
        for model_info in recommended:
            col_name, col_desc, col_btn = st.columns([2, 3, 1])
            with col_name:
                st.markdown(f"**`{model_info['name']}`**")
            with col_desc:
                st.caption(model_info["description"])
            with col_btn:
                if st.button(t("ollama_pull_btn"), key=f"pull_{model_info['name']}", use_container_width=True):
                    with st.spinner(t("ollama_pulling")):
                        import subprocess
                        try:
                            subprocess.run(["ollama", "pull", model_info["name"]], check=True, timeout=600)
                            st.success(t("ollama_pull_ok"))
                            st.rerun()
                        except Exception as e:
                            st.error(f"{t('ollama_pull_fail')}: {e}")


def show_settings_page():
    """Settings page for LLM configuration."""
    st.title(t("settings_title"))

    settings = get_settings()

    # ── Language ──────────────────────────────────────────────────────────────
    st.subheader(t("settings_language_title"))
    current_lang = get_language()
    lang_options = list(SUPPORTED_LANGUAGES.keys())
    lang_labels = list(SUPPORTED_LANGUAGES.values())
    lang_idx = lang_options.index(current_lang) if current_lang in lang_options else 0
    selected_lang = st.selectbox(
        t("settings_language_label"),
        lang_options,
        index=lang_idx,
        format_func=lambda x: SUPPORTED_LANGUAGES[x],
    )
    if selected_lang != current_lang:
        set_language(selected_lang)
        st.rerun()

    st.divider()

    # ── Provider ──────────────────────────────────────────────────────────────
    st.subheader(t("settings_provider"))

    providers = ["ollama", "anthropic", "openai", "google"]
    current_idx = providers.index(settings.llm_provider) if settings.llm_provider in providers else 0
    provider = st.selectbox(t("settings_select_provider"), providers, index=current_idx)

    api_key = ""
    base_url = ""
    model = ""
    timeout = _DEFAULT_TIMEOUT.get(provider, 120)

    # ── Provider-specific fields ──────────────────────────────────────────────
    if provider == "ollama":
        _show_ollama_setup()

        base_url = st.text_input(
            t("settings_ollama_url"),
            value=settings.ollama_base_url,
            help=t("settings_ollama_url_help"),
        )

        # Discover available models
        ollama_models = _get_ollama_models(base_url)
        if ollama_models:
            st.success(f"{t('settings_ollama_connected')} — {len(ollama_models)} {t('settings_ollama_models_available')}")
            default_model = settings.llm_model if settings.llm_model in ollama_models else ollama_models[0]
            model = st.selectbox(
                t("settings_ollama_model"),
                ollama_models,
                index=ollama_models.index(default_model),
            )
        else:
            st.warning(t("settings_ollama_unreachable"))
            model = st.text_input(
                t("settings_ollama_model_manual"),
                value=settings.llm_model if settings.llm_provider == "ollama" else "gemma3:4b",
                help=t("settings_ollama_model_hint"),
            )

        timeout = st.slider(
            t("settings_timeout"),
            min_value=60, max_value=600,
            value=_DEFAULT_TIMEOUT["ollama"],
            step=30,
            help=t("settings_timeout_help"),
        )

    elif provider in ("anthropic", "openai", "google"):
        _provider_labels = {"anthropic": "Anthropic", "openai": "OpenAI", "google": "Google"}
        api_key = st.text_input(
            f"{t('settings_api_key')} {_provider_labels[provider]}",
            value=getattr(settings, f"{provider}_api_key"),
            type="password",
            autocomplete="off",
            help=t("settings_api_key_help"),
        )

        # Refresh button clears the cached live list before re-querying.
        if st.button(t("settings_models_refresh"), key=f"refresh_{provider}"):
            from app.llm.providers import model_catalog
            model_catalog.clear_cache(provider)
            st.rerun()

        models, live = _get_api_models(provider, api_key)
        if live:
            st.success(f"{t('settings_models_live')} — {len(models)}")
        else:
            st.caption(t("settings_models_fallback"))

        default_model = settings.llm_model if settings.llm_model in models else models[0]
        model = st.selectbox(
            t("settings_model"),
            models,
            index=models.index(default_model),
        )

    # ── Hugging Face token ────────────────────────────────────────────────────
    st.divider()
    st.subheader(t("settings_embedding_title"))
    hf_token = st.text_input(
        t("settings_hf_token"),
        value=settings.hf_token,
        type="password",
        autocomplete="off",
        help=t("settings_hf_token_help"),
    )

    # ── Generation parameters ─────────────────────────────────────────────────
    st.divider()
    st.subheader(t("settings_gen_params"))

    temperature = st.slider(
        t("settings_temperature"),
        0.0, 1.0,
        value=st.session_state.get("temperature", settings.temperature),
        step=0.05,
        help=t("settings_temperature_help"),
    )
    max_tokens = st.number_input(
        t("settings_max_tokens"),
        min_value=512, max_value=4000,
        value=min(4000, int(st.session_state.get("max_tokens", settings.max_tokens))),
        step=512,
    )
    daily_token_budget = st.number_input(
        t("settings_daily_budget"),
        min_value=1000,
        max_value=10_000_000,
        value=settings.daily_token_budget,
        step=1000,
    )

    # ── Actions ───────────────────────────────────────────────────────────────
    st.divider()
    col_test, col_save = st.columns(2)

    with col_test:
        if st.button(t("settings_test_connection"), type="primary", use_container_width=True):
            with st.spinner(t("settings_testing")):
                try:
                    router = _init_router(
                        provider,
                        api_key,
                        model,
                        base_url,
                        timeout,
                        temperature,
                        max_tokens,
                    )
                    if router.test_connection():
                        st.success(t("settings_connection_ok"))
                        logger.info("Connection OK: provider=%s model=%s", provider, model)

                        # Update session state
                        st.session_state["llm_connected"] = True
                        st.session_state["llm_provider"] = provider
                        st.session_state["llm_model"] = model
                        st.session_state["llm_base_url"] = base_url
                        st.session_state["llm_timeout"] = timeout
                        st.session_state["router"] = router
                        st.session_state["temperature"] = temperature
                        st.session_state["max_tokens"] = max_tokens

                        # Initialize RAG pipeline
                        pipeline = _init_pipeline(router)
                        if pipeline:
                            st.session_state["pipeline"] = pipeline
                            st.success(t("settings_pipeline_ready"))
                    else:
                        st.error(t("settings_connection_failed"))
                        logger.warning("Connection failed: provider=%s", provider)
                except Exception as e:
                    st.error(f"{t('chat_error')}: {e}")
                    logger.exception("Connection test error: provider=%s", provider)

    with col_save:
        if st.button(t("settings_save"), use_container_width=True,
                     help=t("settings_save_help")):
            updates = {
                "llm_provider": provider,
                "llm_model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "daily_token_budget": daily_token_budget,
                "hf_token": hf_token,
            }
            if provider == "ollama":
                updates["ollama_base_url"] = base_url
            elif api_key:
                if provider == "anthropic":
                    updates["anthropic_api_key"] = api_key
                elif provider == "openai":
                    updates["openai_api_key"] = api_key
                elif provider == "google":
                    updates["google_api_key"] = api_key

            try:
                save_settings_to_env(updates)
                st.success(f"{t('settings_saved')} Provider: **{provider}** / Model: **{model}**")
                logger.info("Settings saved to .env: %s", updates)
            except Exception as e:
                st.error(f"{t('settings_save_error')}: {e}")
                logger.exception("Error saving settings to .env")

    # ── Status panel ──────────────────────────────────────────────────────────
    st.divider()
    st.subheader(t("settings_system_status"))

    status_cols = st.columns(3)
    with status_cols[0]:
        connected = st.session_state.get("llm_connected", False)
        st.metric(
            t("settings_active_provider"),
            st.session_state.get("llm_provider", "—"),
            delta=t("settings_connected") if connected else t("settings_not_configured"),
            delta_color="normal" if connected else "inverse",
        )
    with status_cols[1]:
        st.metric(t("settings_model"), st.session_state.get("llm_model", "—"))
    with status_cols[2]:
        try:
            from app.rag.retriever import get_chroma_client
            client = get_chroma_client(str(CHROMA_PERSIST_DIR))
            coll = client.get_collection("raggy_kb")
            st.metric(t("settings_kb_chunks"), coll.count())
        except Exception:
            st.metric(t("settings_kb_chunks"), "—", delta=t("settings_kb_not_indexed"), delta_color="inverse")

    with st.expander(t("settings_config_details")):
        st.json({
            "provider (.env)": settings.llm_provider,
            "model (.env)": settings.llm_model,
            "ollama_url": settings.ollama_base_url,
            "embedding_model": settings.embedding_model,
            "daily_token_budget": settings.daily_token_budget,
            "chroma_dir": str(CHROMA_PERSIST_DIR),
            "session_provider": st.session_state.get("llm_provider", "—"),
            "session_model": st.session_state.get("llm_model", "—"),
        })

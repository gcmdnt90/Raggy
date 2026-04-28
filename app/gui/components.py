"""Reusable GUI components for Raggy."""

import streamlit as st
from app.i18n import t
from app.utils.token_budget import get_daily_budget, get_daily_usage, is_budget_exhausted


def render_header():
    """Header with title."""
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        st.markdown("### 🧠")
    with col_title:
        st.title(t("app_title"))
        st.caption(t("app_subtitle"))


def render_privacy_warning():
    """Privacy notice when using a cloud API provider."""
    provider = st.session_state.get("llm_provider", "")
    if provider in ("anthropic", "openai", "google"):
        st.warning(t("privacy_warning"))


def _reset_conversation_state() -> None:
    """Clear chat-related session state and pipeline memory."""
    for key in (
        "chat_messages",
        "admin_chat_messages",
        "pending_chat",
        "pending_prompt",
        "cached_analysis",
        "analysis_cache",
    ):
        st.session_state.pop(key, None)
    pipeline = st.session_state.get("pipeline")
    memory = getattr(pipeline, "memory", None)
    if memory and hasattr(memory, "clear"):
        memory.clear()


def render_budget_status() -> bool:
    """Render the daily token budget status and return True if exhausted."""
    used = get_daily_usage()
    budget = get_daily_budget()
    exhausted = is_budget_exhausted()
    if exhausted:
        st.error(t("budget_reached"))
    else:
        st.caption(t("budget_used", used=used, budget=budget))
    return exhausted


def render_sidebar():
    """Sidebar with navigation and LLM status."""
    with st.sidebar:
        st.title(f"🧠 {t('app_title')}")
        st.caption(t("app_subtitle"))
        st.divider()

        page = st.radio(t("nav_navigation"), [
            t("nav_chat"),
            t("nav_settings"),
        ])

        st.divider()

        # LLM connection status
        if st.session_state.get("llm_connected"):
            provider = st.session_state.get("llm_provider", "?")
            model = st.session_state.get("llm_model", "?")
            st.success(f"LLM: {provider} — {model}")
        else:
            st.warning(t("llm_not_configured"))
            st.caption(t("llm_go_settings"))

        st.divider()

        if st.button(t("reset_conversation"), use_container_width=True):
            _reset_conversation_state()
            st.rerun()

        st.caption(t("budget_used", used=get_daily_usage(), budget=get_daily_budget()))
        st.divider()
        st.caption(t("version_label"))

    return page

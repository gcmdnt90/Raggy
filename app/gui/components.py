"""Reusable GUI components for Raggy."""

import streamlit as st
from app.i18n import t


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
        st.caption(t("version_label"))

    return page

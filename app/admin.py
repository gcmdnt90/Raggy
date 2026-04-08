"""Raggy — Admin panel Streamlit entry point."""

import streamlit as st

st.set_page_config(
    page_title="Raggy Admin",
    page_icon="🧠",
    layout="wide",
)

# Configure logging once per process (idempotent)
from app.utils.logging_config import setup_logging
setup_logging()

import logging
logger = logging.getLogger(__name__)
logger.info("Raggy admin panel started")

from app.gui.admin_panel import (
    check_admin_auth,
    admin_chatbot,
    admin_prompt_editor,
    admin_kb_manager,
    admin_logs,
)
from app.gui.settings import show_settings_page
from app.i18n import t

if not check_admin_auth():
    st.stop()

# Sidebar
with st.sidebar:
    st.title(f"🧠 {t('admin_title')}")
    st.divider()

    section = st.radio(t("nav_navigation"), [
        t("admin_section_chatbot"),
        t("admin_section_prompts"),
        t("admin_section_kb"),
        t("admin_section_settings"),
        t("admin_section_logs"),
    ])

    st.divider()
    if st.button(t("admin_logout")):
        st.session_state["admin_authenticated"] = False
        st.rerun()

# Route
if section == t("admin_section_chatbot"):
    admin_chatbot()
elif section == t("admin_section_prompts"):
    admin_prompt_editor()
elif section == t("admin_section_kb"):
    admin_kb_manager()
elif section == t("admin_section_settings"):
    show_settings_page()
elif section == t("admin_section_logs"):
    admin_logs()

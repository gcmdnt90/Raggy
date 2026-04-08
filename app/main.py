"""Raggy — Main Streamlit entry point."""

import streamlit as st

st.set_page_config(
    page_title="Raggy — Knowledge Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Configure logging once per process (idempotent)
from app.utils.logging_config import setup_logging
setup_logging()

import logging
logger = logging.getLogger(__name__)
logger.info("Raggy main app started")

from app.gui.components import render_sidebar
from app.gui.chat import show_chatbot_page
from app.gui.settings import show_settings_page
from app.i18n import t

# Render sidebar and get selected page
page = render_sidebar()

# Route to selected page
if page == t("nav_chat"):
    show_chatbot_page()
elif page == t("nav_settings"):
    show_settings_page()

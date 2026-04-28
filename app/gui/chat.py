"""Chat component for Raggy — generic knowledge base chatbot."""

import logging

import streamlit as st
from app.gui.components import render_budget_status, render_privacy_warning
from app.i18n import t

logger = logging.getLogger(__name__)


def _get_pipeline():
    """Return the RAG pipeline from session, or None."""
    return st.session_state.get("pipeline")


def show_chatbot_page():
    """Chatbot page for knowledge base Q&A."""
    st.title(t("chat_title"))
    st.caption(t("chat_subtitle"))
    render_privacy_warning()

    pipeline = _get_pipeline()
    if not pipeline:
        st.warning(t("chat_configure_llm"))
    budget_exhausted = render_budget_status()

    # Init chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # Consume any pending suggestion from a button click
    pending_prompt: str | None = st.session_state.pop("pending_chat", None)

    # Quick suggestions — shown only when there is no history and no pending message
    if not st.session_state.chat_messages and not pending_prompt:
        st.info(t("chat_suggestions_title"))
        suggestions = [
            t("chat_sugg_1"),
            t("chat_sugg_2"),
            t("chat_sugg_3"),
            t("chat_sugg_4"),
        ]
        cols = st.columns(2)
        for i, sugg in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(sugg, key=f"sugg_{i}", use_container_width=True):
                    st.session_state["pending_chat"] = sugg
                    st.rerun()

    # Show existing history
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Accept input
    typed_prompt = st.chat_input(
        t("chat_placeholder"),
        max_chars=4000,
        disabled=budget_exhausted,
    )
    prompt = typed_prompt or pending_prompt

    if prompt and not budget_exhausted:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if pipeline:
                try:
                    logger.info("Chat query: %s", prompt[:100])
                    response = st.write_stream(
                        pipeline.chat_stream_sync(prompt)
                    )
                    logger.debug("Chat response: %d chars", len(response))
                    st.session_state.chat_messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    logger.exception("Chat error: query=%s", prompt[:100])
                    error_msg = f"{t('chat_error')}: {e}"
                    st.error(error_msg)
                    st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
            else:
                msg = t("chat_configure_msg")
                st.warning(msg)
                st.session_state.chat_messages.append({"role": "assistant", "content": msg})

"""Admin Panel for Raggy — KB management, prompts, LLM config."""

import logging
import streamlit as st
from secrets import compare_digest
from pathlib import Path
from app.config import get_settings, KB_ROOT, CHROMA_PERSIST_DIR, PROMPTS_DIR
from app.i18n import t

logger = logging.getLogger(__name__)


def check_admin_auth() -> bool:
    """Simple password authentication."""
    if st.session_state.get("admin_authenticated"):
        return True

    st.title(t("admin_login_title"))
    password = st.text_input(t("admin_password"), type="password", autocomplete="off")

    if st.button(t("admin_login")):
        settings = get_settings()
        if compare_digest(password, settings.admin_password):
            st.session_state["admin_authenticated"] = True
            st.rerun()
        else:
            st.error(t("admin_wrong_password"))

    return False


# ── Admin Chatbot ──────────────────────────────────────────────────────────────

def admin_chatbot():
    """Section: Admin Chatbot for platform management."""
    st.subheader(t("admin_section_chatbot"))

    pipeline = st.session_state.get("pipeline")
    if not pipeline:
        st.warning(t("chat_configure_llm"))
        return

    # Load admin system prompt
    try:
        from app.llm.prompts.system import PromptManager
        pm = PromptManager()
        system_prompt = pm.get_admin_system_prompt()
    except Exception:
        system_prompt = (
            "You are the administrative assistant for Raggy, a RAG-powered knowledge platform. "
            "Help the admin manage prompts, Knowledge Base, and configuration. "
            "Respond in the user's language."
        )

    # Separate chat state from user chat
    if "admin_chat_messages" not in st.session_state:
        st.session_state.admin_chat_messages = []

    col_chat, col_ctrl = st.columns([5, 1])
    with col_ctrl:
        if st.button("🔄", use_container_width=True):
            st.session_state.admin_chat_messages = []
            st.rerun()

    # Message history
    for msg in st.session_state.admin_chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input(t("chat_placeholder"), max_chars=4000)

    if prompt:
        st.session_state.admin_chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            from app.llm.base import LLMMessage

            history = [
                LLMMessage(role=m["role"], content=m["content"])
                for m in st.session_state.admin_chat_messages[:-1]
            ]
            messages = [
                LLMMessage(role="system", content=system_prompt),
                *history,
                LLMMessage(role="user", content=prompt),
            ]

            try:
                response = st.write_stream(
                    pipeline.router.generate_stream(messages, temperature=0.4)
                )
                st.session_state.admin_chat_messages.append({"role": "assistant", "content": response})
            except Exception as e:
                logger.exception("Admin chat error: %s", prompt[:80])
                st.error(f"{t('chat_error')}: {e}")


# ── Prompt Editor ──────────────────────────────────────────────────────────────

def admin_prompt_editor():
    """Section: System Prompt Editor."""
    st.subheader(t("prompts_title"))

    prompt_files = {
        t("prompts_chatbot"): "system_chatbot.yaml",
        t("prompts_admin"): "system_admin.yaml",
    }

    prompt_type = st.selectbox(t("prompts_type"), list(prompt_files.keys()))
    yaml_file = PROMPTS_DIR / prompt_files[prompt_type]

    current_prompt = ""
    if yaml_file.exists():
        import yaml
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            current_prompt = data.get("prompt", "")

    edited_prompt = st.text_area(
        "System prompt",
        value=current_prompt,
        height=400,
        help=t("prompts_textarea_help"),
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(t("prompts_save"), type="primary"):
            import yaml
            yaml_file.parent.mkdir(parents=True, exist_ok=True)
            with open(yaml_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    {"name": f"System Prompt - {prompt_type}", "version": "1.0", "prompt": edited_prompt},
                    f, allow_unicode=True, default_flow_style=False,
                )
            st.success(t("prompts_saved"))

    with col2:
        if st.button(t("prompts_reset")):
            st.info("Re-run KB ingestion to restore default prompts.")


# ── Knowledge Base Manager ─────────────────────────────────────────────────────

def admin_kb_manager():
    """Section: Knowledge Base Manager with upload wizard."""
    st.subheader(t("kb_title"))

    # Stats
    col1, col2 = st.columns(2)

    from app.parsers.documents import SUPPORTED_EXTENSIONS

    all_files = [
        path for path in KB_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    # Exclude chroma_db and README
    kb_files = [f for f in all_files if "chroma_db" not in str(f)]
    col1.metric(t("kb_docs_md"), len(kb_files))

    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
        coll = client.get_collection("raggy_kb")
        col2.metric(t("kb_chunks_indexed"), coll.count())
    except Exception:
        col2.metric(t("kb_chunks_indexed"), "N/A")

    st.divider()

    # ── File browser with View / Edit ──────────────────────────────────────────
    st.write(f"**{t('kb_files_in_kb')}**")

    # State for view/edit
    if "kb_active_file" not in st.session_state:
        st.session_state.kb_active_file = None
    if "kb_active_mode" not in st.session_state:
        st.session_state.kb_active_mode = None

    # Auto-discover categories (subdirectories)
    categories = sorted([
        d.name for d in KB_ROOT.iterdir()
        if d.is_dir() and d.name not in ("chroma_db", "__pycache__", "prompts")
    ])

    for cat in categories:
        cat_dir = KB_ROOT / cat
        files = sorted([f for f in cat_dir.iterdir() if f.is_file()])
        if not files:
            continue

        with st.expander(f"{cat} ({len(files)} files)"):
            for fpath in files:
                is_text = fpath.suffix in (".md", ".txt")
                col_name, col_view, col_edit, col_del = st.columns([5, 1, 1, 1])

                with col_name:
                    size_kb = fpath.stat().st_size / 1024
                    st.markdown(f"`{fpath.name}` — {size_kb:.1f} KB")

                key_base = fpath.as_posix().replace("/", "_").replace(".", "_")

                with col_view:
                    if is_text:
                        if st.button(f"👁 {t('kb_view')}", key=f"view_{key_base}", use_container_width=True):
                            if (st.session_state.kb_active_file == fpath and st.session_state.kb_active_mode == "view"):
                                st.session_state.kb_active_file = None
                                st.session_state.kb_active_mode = None
                            else:
                                st.session_state.kb_active_file = fpath
                                st.session_state.kb_active_mode = "view"
                            st.rerun()

                with col_edit:
                    if is_text:
                        if st.button(f"✏️ {t('kb_edit')}", key=f"edit_{key_base}", use_container_width=True):
                            if (st.session_state.kb_active_file == fpath and st.session_state.kb_active_mode == "edit"):
                                st.session_state.kb_active_file = None
                                st.session_state.kb_active_mode = None
                            else:
                                st.session_state.kb_active_file = fpath
                                st.session_state.kb_active_mode = "edit"
                            st.rerun()

                with col_del:
                    if st.button("🗑", key=f"del_{key_base}", use_container_width=True):
                        st.session_state[f"confirm_del_{key_base}"] = True
                        st.rerun()

                # Delete confirmation
                if st.session_state.get(f"confirm_del_{key_base}"):
                    st.warning(f"{t('kb_delete_confirm')} **{fpath.name}**?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button(t("kb_delete_yes"), key=f"yes_del_{key_base}", type="primary"):
                            fpath.unlink()
                            st.session_state.pop(f"confirm_del_{key_base}", None)
                            if st.session_state.kb_active_file == fpath:
                                st.session_state.kb_active_file = None
                                st.session_state.kb_active_mode = None
                            st.success(f"{fpath.name} {t('kb_deleted')}")
                            st.rerun()
                    with c2:
                        if st.button(t("kb_cancel"), key=f"no_del_{key_base}"):
                            st.session_state.pop(f"confirm_del_{key_base}", None)
                            st.rerun()

                # VIEW panel
                if (st.session_state.kb_active_file == fpath and st.session_state.kb_active_mode == "view"):
                    with st.container(border=True):
                        st.caption(f"📄 {fpath.name}")
                        content = fpath.read_text(encoding="utf-8")
                        if fpath.suffix == ".md":
                            st.markdown(content)
                        else:
                            st.code(content, language="text")
                        if st.button(t("kb_close"), key=f"close_view_{key_base}"):
                            st.session_state.kb_active_file = None
                            st.session_state.kb_active_mode = None
                            st.rerun()

                # EDIT panel
                if (st.session_state.kb_active_file == fpath and st.session_state.kb_active_mode == "edit"):
                    with st.container(border=True):
                        st.caption(f"✏️ {fpath.name}")
                        original = fpath.read_text(encoding="utf-8")
                        edited = st.text_area(
                            "Content",
                            value=original,
                            height=400,
                            key=f"textarea_{key_base}",
                            label_visibility="collapsed",
                        )
                        c1, c2, c3 = st.columns([2, 2, 3])
                        with c1:
                            if st.button(f"💾 {t('kb_save')}", key=f"save_{key_base}", type="primary"):
                                fpath.write_text(edited, encoding="utf-8")
                                st.success(t("kb_saved"))
                                st.session_state.kb_active_file = None
                                st.session_state.kb_active_mode = None
                                st.rerun()
                        with c2:
                            if st.button(f"✖ {t('kb_cancel')}", key=f"cancel_edit_{key_base}"):
                                st.session_state.kb_active_file = None
                                st.session_state.kb_active_mode = None
                                st.rerun()
                        with c3:
                            st.caption(t("kb_no_reindex_note"))

    st.divider()

    # ── Upload ─────────────────────────────────────────────────────────────────
    st.write(f"**{t('kb_upload_title')}**")
    uploaded = st.file_uploader(t("kb_upload_file"), type=["md", "txt", "pdf", "docx", "xlsx"])

    # Category selection: existing + create new
    existing_cats = categories if categories else []
    cat_options = existing_cats + ["+ New category"]
    category = st.selectbox(t("kb_category"), cat_options)

    new_cat_name = ""
    if category == "+ New category":
        new_cat_name = st.text_input(t("kb_new_category"))
        category = new_cat_name.strip().lower().replace(" ", "_") if new_cat_name.strip() else ""
    category = "".join(ch for ch in category if ch.isalnum() or ch in ("_", "-"))

    if uploaded and category and st.button(t("kb_add_btn")):
        safe_name = Path(uploaded.name).name
        suffix = Path(safe_name).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            st.error(t("kb_unsupported_file"))
            return
        data = uploaded.getvalue()
        try:
            from app.utils.sanitize import (
                validate_docx,
                validate_pdf,
                validate_text_bytes,
                validate_xlsx,
            )
            if suffix in (".md", ".txt"):
                validate_text_bytes(data)
            elif suffix == ".pdf":
                validate_pdf(data)
            elif suffix == ".docx":
                validate_docx(data)
            elif suffix == ".xlsx":
                validate_xlsx(data)
        except Exception as exc:
            st.error(f"{t('kb_upload_invalid')}: {exc}")
            return
        target_dir = (KB_ROOT / category).resolve()
        target = (target_dir / safe_name).resolve()
        if KB_ROOT.resolve() not in target.parents:
            st.error(t("kb_unsafe_path"))
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        st.success(f"'{uploaded.name}' {t('kb_added')} '{category}'")

    st.divider()

    # Reindex
    if st.button(t("kb_reindex_btn"), type="primary"):
        with st.spinner(t("kb_reindexing")):
            # Release ChromaDB file locks before rebuild can delete the DB
            from app.rag.retriever import close_chroma_clients
            close_chroma_clients()
            import gc; gc.collect()

            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
            from scripts.ingest_kb import main as ingest_main
            ingest_main(rebuild=True)
        st.success(t("kb_reindexed"))


# ── Log ────────────────────────────────────────────────────────────────────────

def admin_logs():
    """Section: Logs and usage."""
    st.subheader(t("logs_title"))

    from app.utils.logger import load_recent_logs, count_today_logs, count_total_reports

    col1, col2 = st.columns(2)
    col1.metric(t("logs_today"), count_today_logs())
    col2.metric(t("logs_total"), count_total_reports())

    st.divider()
    st.write(f"**{t('logs_recent')}**")
    logs = load_recent_logs(n=20)
    if not logs:
        st.info(t("logs_none"))
    for log in logs:
        with st.expander(f"{log['timestamp'][:19]} — {log['type']} ({log.get('provider', '?')})"):
            st.write(f"**Query:** {log.get('query', '')[:200]}...")
            st.write(f"**Response:** {log.get('response_preview', '')[:200]}...")
            if log.get("tokens"):
                st.write(f"**Tokens:** {log['tokens']}")

// English — Banco's second language. See app/web/shared/i18n.js.
//
// Keys must match strings.it.js exactly; tests/test_i18n.py fails if the two
// catalogues drift apart, because a key present in one and missing from the
// other shows the room a raw key on a projected screen.

window.BancoStrings = window.BancoStrings || {};
window.BancoStrings.en = {
  // ── shared ────────────────────────────────────────────────────────────
  "common.language": "language",
  "common.language_aria": "Interface language",

  // ── harness, static ───────────────────────────────────────────────────
  "harness.sector": "sector",
  "harness.sector_aria": "Sector",
  "harness.profile_title": "derived from what this machine can actually reach",
  "harness.egress_title": "where calls went",
  "harness.egress_label": "egress",
  "harness.demonstrations": "Demonstrations",
  "harness.demos_aria": "demonstrations",
  "harness.current_sequence": "Current sequence",
  "harness.beats_aria": "beats",
  "harness.prompt_summary": "prompt as sent",
  "harness.prompt_summary_template": "the prompt — material not pasted yet",
  "harness.prompt_summary_edited": "prompt as sent — edited by hand",
  "harness.run": "Run",

  // ── harness, built in JavaScript ──────────────────────────────────────
  "harness.no_source_configured": "no model source configured",
  "harness.beat_panes": "{count} panes",
  "harness.beat_no_panes": "—",
  "harness.reset_run": "Clear this beat",
  "harness.beats_show_all": "also show the {count} that cannot run",
  "harness.beats_show_runnable": "show only the runnable ones",
  "harness.context_all": "all documents — {chars} characters in context",
  "harness.context_retrieved": "{count} retrieved passages",
  "harness.passage_score": "score {score}",
  "harness.gear_title": "model sources for this beat",
  "harness.gear_loading": "reading the configured sources…",
  "harness.gear_none": "no configured source to choose from",
  "harness.gear_default": "as the profile says",
  "harness.gear_think_off": "no reasoning",
  "harness.gear_note": "Applies to the next run. A parameter written in the run block still wins: it is what the beat teaches.",
  "harness.open_prompt": "Open and edit",
  "harness.prompt_edited": "edited by hand — applies to the next run",
  "harness.viewer_close": "Back to the overview",
  "harness.viewer_bigger": "bigger",
  "harness.viewer_smaller": "smaller",
  "harness.zoom_pane": "open full page",
  "harness.document_loading": "opening the document…",
  "harness.document_failed": "could not open the document: {error}",
  "harness.not_executable": "not executable",
  "harness.run_continues": "Run — continues {beat}",
  "harness.mode_live": "LIVE",
  "harness.mode_replay": "REPLAY — a recording of a real run",
  "harness.pane_waiting": "waiting",
  "harness.pane_streaming": "streaming",
  "harness.pane_done": "done",
  "harness.pane_failed": "failed",
  "harness.pane_unavailable": "unavailable",
  "harness.unavailable": "unavailable",
  "harness.temperature": "temp {value}",
  "harness.temperature_ignored": "temp {value} not sent — this provider does not accept one",
  "harness.thinking": "thinking {level}",
  "harness.local": "local",
  "harness.degraded":
    "Degraded: not every pane has a model source. Unavailable panes are " +
    "marked, never filled in.",
  "harness.chain_written": "chain file written: {file}",
  "harness.chain_held":
    "Chain file left untouched: not every pane succeeded, so the version that " +
    "shipped is still in place.",
  "harness.chain_failed": "chain file not written: {error}",
  "harness.run_refused": "run refused ({status})",
  "harness.replaying": "{reason} — replaying a recording",
  "harness.no_recording":
    "{reason}. No recording exists yet, so nothing is shown here rather than " +
    "something invented.",
  "harness.server_unreachable": "cannot reach the server: {error}",

  // ── stage console, static ─────────────────────────────────────────────
  "console.where": "stage console — not for the projector",
  "console.open_harness": "open the harness →",
  "console.unprotected":
    "This console has no password. Anything running on this machine can reach " +
    "it. Set one under Access, below.",
  "console.nav_aria": "Console sections",
  "console.nav_title": "Stage console",
  "console.nav_overview": "Overview",
  "console.nav_sources": "Model sources",
  "console.nav_local": "Local model",
  "console.nav_material": "Demo material",
  "console.heading": "Pre-flight",
  "console.sources_title": "Model sources",
  "console.sources_lead":
    "At least one is required; two make every pane of D1 live. Keys are " +
    "stored in .env and never displayed again — leave a field blank to keep " +
    "what is already there.",
  "console.access": "Access",
  "console.console_password": "Console password",
  "console.password_placeholder": "choose one",
  "console.save": "Save",
  "console.material_title": "Demo material",
  "console.material_lead":
    "Every demonstration reads files from the sector's pack. A sector is " +
    "either complete or it cannot run — this is checked for all five demos, " +
    "not only the ones Banco can execute yet.",
  "console.sector": "Sector",
  "console.ollama_title": "Local model — Ollama",
  "console.checking": "checking…",
  "console.address": "Address",
  "console.installed_heading": "Installed",
  "console.recommended_heading": "Recommended for this machine",
  "console.readiness": "Readiness",
  "console.readiness_lead":
    "Read from this machine. The live check calls every configured source " +
    "once — it is the only line that can tell a working key from a stored " +
    "one, and it reports the reason when one fails.",
  "console.run_check": "Run the full check",
  "console.forget_transcripts": "Forget rehearsal transcripts",
  "console.transcripts_note":
    "A beat that continues an earlier one interrogates what its pane said " +
    "before. After a dry run those answers are still in memory.",

  // ── stage console, built in JavaScript ────────────────────────────────
  "console.key_stored": "key stored",
  "console.not_set": "not set",
  "console.is_set": "set",
  "console.ollama_running": "running",
  "console.ollama_installed_not_running": "installed, not running",
  "console.ollama_not_installed": "not installed",
  "console.ollama_reachable": "Reachable at {url}",
  "console.ollama_ram": "{gb} GB RAM",
  "console.ollama_installed_hint": "Installed but not answering. Start Ollama, then reload.",
  "console.ollama_absent_hint":
    "Not installed. Banco runs without it; the offline profile does not.",
  "console.none": "none",
  "console.dash": "—",
  "console.pull": "pull",
  "console.pulling": "pulling {model}",
  "console.calling_sources": "calling each source…",
  "console.all_sources_live": "every configured source answered",
  "console.some_sources_dead": "at least one source did not answer — see below",
  "console.no_source_to_call": "no source configured to call",
  "console.could_not_save": "could not save",
  "console.forgotten": "Forgotten",
  "console.preflight_failed": "pre-flight could not be read: {error}",

  // ── stage console, demo material ──────────────────────────────────────
  "console.no_sector": "no sector in the demo database",
  "console.sector_missing": " — pack missing",
  "console.sector_ready": "pack on disk",
  "console.sector_incomplete": "pack incomplete",
  "console.unknown_sector": "unknown sector",
  "console.material_ok": "{count} files present",
  "console.material_missing": "missing {count} of {total} — {names}",
  "console.material_trainer": " (trainer)",
  "console.deck":
    "demo database v{version} · {updated} · theory-deck {pin} · " +
    "{demos} demos · {sectors} sectors",
};

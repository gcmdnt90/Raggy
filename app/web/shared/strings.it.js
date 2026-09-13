// Italian — Banco's default language. See app/web/shared/i18n.js.
//
// Vocabulary the lesson teaches is not translated: `beat`, `replay`, `live`,
// `egress`, `prompt`, `pre-flight`, `harness`, `stage console`. CONTEXT.md
// defines those words and the room is taught them; renaming one here would
// rename a concept halfway through a workshop.

window.BancoStrings = window.BancoStrings || {};
window.BancoStrings.it = {
  // ── shared ────────────────────────────────────────────────────────────
  "common.language": "lingua",
  "common.language_aria": "Lingua dell'interfaccia",

  // ── harness, static ───────────────────────────────────────────────────
  "harness.sector": "settore",
  "harness.sector_aria": "Settore",
  "harness.profile_title": "ricavato da ciò che questa macchina raggiunge davvero",
  "harness.egress_title": "dove sono andate le chiamate",
  "harness.egress_label": "egress",
  "harness.demonstrations": "Dimostrazioni",
  "harness.demos_aria": "dimostrazioni",
  "harness.current_sequence": "Sequenza corrente",
  "harness.beats_aria": "beat",
  "harness.prompt_summary": "il prompt come inviato",
  "harness.run": "Esegui",

  // ── harness, built in JavaScript ──────────────────────────────────────
  "harness.no_source_configured": "nessuna fonte modello configurata",
  "harness.beat_panes": "{count} pannelli",
  "harness.beat_no_panes": "—",
  "harness.not_executable": "non eseguibile",
  "harness.run_continues": "Esegui — continua {beat}",
  "harness.mode_live": "LIVE",
  "harness.mode_replay": "REPLAY — la registrazione di un'esecuzione reale",
  "harness.pane_waiting": "in attesa",
  "harness.pane_streaming": "in corso",
  "harness.pane_done": "finito",
  "harness.pane_failed": "fallito",
  "harness.pane_unavailable": "non disponibile",
  "harness.unavailable": "non disponibile",
  "harness.temperature": "temp {value}",
  "harness.temperature_ignored": "temp {value} non inviata — questo provider non la accetta",
  "harness.thinking": "ragionamento {level}",
  "harness.local": "locale",
  "harness.degraded":
    "Degradato: non tutti i pannelli hanno una fonte modello. I pannelli non " +
    "disponibili sono segnalati, mai riempiti.",
  "harness.chain_written": "file di catena scritto: {file}",
  "harness.chain_held":
    "File di catena lasciato intatto: non tutti i pannelli sono riusciti, " +
    "quindi resta in posto la versione consegnata.",
  "harness.chain_failed": "file di catena non scritto: {error}",
  "harness.run_refused": "esecuzione rifiutata ({status})",
  "harness.replaying": "{reason} — replay di una registrazione",
  "harness.no_recording":
    "{reason}. Non esiste ancora nessuna registrazione, quindi qui non viene " +
    "mostrato nulla anziché qualcosa di inventato.",
  "harness.server_unreachable": "impossibile raggiungere il server: {error}",

  // ── stage console, static ─────────────────────────────────────────────
  "console.where": "stage console — non per il proiettore",
  "console.open_harness": "apri l'harness →",
  "console.unprotected":
    "Questa console non ha una password. Qualunque cosa giri su questa " +
    "macchina può raggiungerla. Impostane una nella sezione Accesso, qui sotto.",
  "console.nav_aria": "Sezioni della console",
  "console.nav_title": "Stage console",
  "console.nav_overview": "Panoramica",
  "console.nav_sources": "Fonti modello",
  "console.nav_local": "Modello locale",
  "console.nav_material": "Materiale demo",
  "console.heading": "Pre-flight",
  "console.sources_title": "Fonti modello",
  "console.sources_lead":
    "Ne serve almeno una; due rendono live ogni pannello di D1. Le chiavi " +
    "vengono salvate in .env e non sono più mostrate — lascia un campo vuoto " +
    "per conservare quella che c'è già.",
  "console.access": "Accesso",
  "console.console_password": "Password della console",
  "console.password_placeholder": "scegline una",
  "console.save": "Salva",
  "console.material_title": "Materiale demo",
  "console.material_lead":
    "Ogni dimostrazione legge file dal pacchetto del settore. Un settore è " +
    "completo oppure non può girare — il controllo copre tutte e cinque le " +
    "demo, non solo quelle che Banco sa già eseguire.",
  "console.sector": "Settore",
  "console.ollama_title": "Modello locale — Ollama",
  "console.checking": "controllo in corso…",
  "console.address": "Indirizzo",
  "console.installed_heading": "Installati",
  "console.recommended_heading": "Consigliati per questa macchina",
  "console.readiness": "Prontezza",
  "console.readiness_lead":
    "Letta da questa macchina. Il controllo live chiama una volta ogni fonte " +
    "configurata: è l'unica riga capace di distinguere una chiave che funziona " +
    "da una soltanto salvata, e riporta il motivo quando una fallisce.",
  "console.run_check": "Esegui il controllo completo",
  "console.forget_transcripts": "Dimentica le trascrizioni di prova",
  "console.transcripts_note":
    "Un beat che continua un beat precedente interroga quello che il suo " +
    "pannello aveva detto. Dopo una prova a vuoto quelle risposte sono ancora " +
    "in memoria.",

  // ── stage console, built in JavaScript ────────────────────────────────
  "console.key_stored": "chiave salvata",
  "console.not_set": "non impostata",
  "console.is_set": "impostata",
  "console.ollama_running": "in esecuzione",
  "console.ollama_installed_not_running": "installato, non in esecuzione",
  "console.ollama_not_installed": "non installato",
  "console.ollama_reachable": "Raggiungibile su {url}",
  "console.ollama_ram": "{gb} GB di RAM",
  "console.ollama_installed_hint": "Installato ma non risponde. Avvia Ollama, poi ricarica.",
  "console.ollama_absent_hint":
    "Non installato. Banco funziona lo stesso; il profilo offline no.",
  "console.none": "nessuno",
  "console.dash": "—",
  "console.pull": "scarica",
  "console.pulling": "scarico {model}",
  "console.calling_sources": "chiamo ogni fonte…",
  "console.all_sources_live": "ogni fonte configurata ha risposto",
  "console.some_sources_dead": "almeno una fonte non ha risposto — vedi sotto",
  "console.no_source_to_call": "nessuna fonte configurata da chiamare",
  "console.could_not_save": "non è stato possibile salvare",
  "console.forgotten": "Dimenticate",
  "console.preflight_failed": "pre-flight non leggibile: {error}",

  // ── stage console, demo material ──────────────────────────────────────
  // A sector with no pack stays in the picker and is marked: chi ha bisogno di
  // sapere che manca è esattamente chi sta per sceglierlo.
  "console.no_sector": "nessun settore nel database delle demo",
  "console.sector_missing": " — pacchetto mancante",
  "console.sector_ready": "pacchetto su disco",
  "console.sector_incomplete": "pacchetto incompleto",
  "console.unknown_sector": "settore sconosciuto",
  "console.material_ok": "{count} file presenti",
  "console.material_missing": "mancano {count} file su {total} — {names}",
  "console.material_trainer": " (formatore)",
  "console.deck":
    "database demo v{version} · {updated} · theory-deck {pin} · " +
    "{demos} demo · {sectors} settori",
};

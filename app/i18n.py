"""Banco i18n — one language per request, never one per process.

Italian is the default. Banco is delivered to Italian clients and the harness is
read by a room that speaks Italian; English is the second language, kept because
the demo database and the documentation are written in it and because a
non-Italian room is a real case.

Two things live here and nothing else:

* :func:`t` — the catalogue of strings Banco *generates*. Pre-flight lines,
  refusal reasons, error text. These are produced by the server and rendered on
  a surface, so they are translated here rather than in the page.
* :func:`localized` — the accessor for strings Banco *carries*. The demo
  database and ``run-blocks.json`` are bilingual by convention: the bare field
  is English and ``<field>_it`` is Italian. Nothing else may know that rule.

The language is a parameter on every call. The previous version of this module
held ``_ui_language`` as module state, inherited from a single-user Streamlit
app; Banco serves two surfaces that can be open at once in two browsers, and a
process-wide language would let the console's setting change what the projector
is showing. Do not reintroduce it.

Strings the *user* wrote — prompt text, model output, a provider's own error
message — are never translated. They are shown as they are.
"""

from __future__ import annotations

from collections.abc import Mapping

#: Language code -> the name of that language, written in it.
SUPPORTED_LANGUAGES: dict[str, str] = {"it": "Italiano", "en": "English"}

#: What Banco speaks when nobody has said otherwise.
DEFAULT_LANGUAGE = "it"

#: Where a missing translation falls back to before giving up on the key. The
#: demo database is authored in English, so English is the language most likely
#: to have an entry.
FALLBACK_LANGUAGE = "en"

#: How a language code maps onto the database's field-naming convention: the
#: bare field is English, `_it` is Italian. One place, so that adding a third
#: language is an entry here rather than a search for string concatenation.
FIELD_SUFFIX: dict[str, str] = {"it": "_it", "en": ""}


def normalize(lang: str | None) -> str:
    """Coerce anything into a supported language code.

    Accepts what a browser or a query string actually sends — ``it-IT``,
    ``IT``, ``it_IT``, ``None`` — and never raises: an unreadable language is a
    reason to speak Italian, not a reason to refuse a request.
    """
    if not lang:
        return DEFAULT_LANGUAGE
    code = str(lang).strip().lower().replace("_", "-").split("-")[0]
    return code if code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def t(key: str, lang: str | None = None, **kwargs) -> str:
    """The string for `key` in `lang`, formatted with `kwargs`.

    A missing key returns the key itself rather than an empty string: a bare
    ``preflight.chain.ok`` on a screen is a bug anyone can see and report,
    whereas a blank line looks like a working feature with nothing to say.
    """
    entry = CATALOG.get(key)
    if entry is None:
        return key

    code = normalize(lang)
    text = entry.get(code) or entry.get(DEFAULT_LANGUAGE) or entry.get(FALLBACK_LANGUAGE) or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (IndexError, KeyError):
            # A malformed placeholder must not take down a pre-flight line.
            return text
    return text


def localized(node: Mapping | None, field: str, lang: str | None = None, default=None):
    """Read `field` from a bilingual database node in `lang`.

    Falls through to the bare (English) field when the translation is absent or
    empty, which is the common case: the demo database translates prompt text
    per sector variant but leaves plenty of nodes English-only.
    """
    if not isinstance(node, Mapping):
        return default
    value = node.get(f"{field}{FIELD_SUFFIX[normalize(lang)]}")
    if value in (None, ""):
        value = node.get(field)
    return default if value in (None, "") else value


# ---------------------------------------------------------------------------
# The catalogue — strings Banco generates.
#
# Keys are namespaced by the module that emits them. Anything rendered on a
# page by JavaScript belongs in app/web/shared/strings.*.js instead; this file
# is only for text that crosses the wire already written.
# ---------------------------------------------------------------------------

CATALOG: dict[str, dict[str, str]] = {
    # ── pre-flight ────────────────────────────────────────────────────────
    "preflight.password.missing": {
        "it": "La stage console non ha una password. È raggiungibile da "
              "qualunque cosa giri su questa macchina.",
        "en": "The stage console has no password. It is reachable by anything "
              "running on this machine.",
    },
    "preflight.password.missing.action": {
        "it": "Impostane una qui sotto. Fino ad allora questa console è aperta.",
        "en": "Set one below. Until then this console is open.",
    },
    "preflight.password.ok": {
        "it": "Password della console impostata.",
        "en": "Console password set.",
    },
    # ── demo material ─────────────────────────────────────────────────────
    # The pack is generated, not shipped, so "missing" here always has the same
    # fix and the line carries it: a trainer reading this is minutes from a
    # lesson, not debugging a checkout.
    "preflight.material.unknown_sector": {
        "it": "Settore sconosciuto: {sector}. Non è nel database delle demo.",
        "en": "Unknown sector: {sector}. It is not in the demo database.",
    },
    "preflight.material.no_pack": {
        "it": "Il pacchetto di questo settore non è stato generato: {root}",
        "en": "The pack for this sector does not exist: {root}",
    },
    "preflight.material.incomplete": {
        "it": "{count} demo su {total} hanno materiale mancante: {names}",
        "en": "{count} of {total} demos are missing material: {names}",
    },
    "preflight.material.action": {
        "it": "Generalo con:  {command}",
        "en": "Generate it with:  {command}",
    },
    "preflight.material.ok": {
        "it": "Materiale completo per tutte e {total} le demo.",
        "en": "Material complete for all {total} demos.",
    },
    "preflight.chain.unknown_sector": {
        "it": "Settore sconosciuto: {sector}.",
        "en": "Unknown sector: {sector}.",
    },
    "preflight.chain.missing": {
        "it": "{missing} file di consegna su {total} mancanti: {names}",
        "en": "{missing} of {total} handover files missing: {names}",
    },
    "preflight.chain.missing.action": {
        "it": "Rigenerali con demo/kit/generate_chain.py prima della lezione.",
        "en": "Regenerate them with demo/kit/generate_chain.py before the lesson.",
    },
    # The files are all there, so the chain has not stopped. What it is about
    # to hand the next demo is material in another language, which reads on a
    # projected screen as a model that answered in the wrong one.
    "preflight.chain.other_language": {
        "it": "{count} file della catena sono stati scritti in un'altra lingua: "
              "{names}. Il prossimo modulo li incollerebbe sotto un prompt "
              "italiano.",
        "en": "{count} chain files were written in another language: {names}. "
              "The next module would paste them under an English prompt.",
    },
    "preflight.chain.other_language.action": {
        "it": "Riesegui quei moduli nella lingua della lezione, oppure "
              "rigenera la catena con demo/kit/generate_chain.py.",
        "en": "Re-run those modules in the language of the lesson, or "
              "regenerate the chain with demo/kit/generate_chain.py.",
    },
    "preflight.chain.ok": {
        "it": "Tutti i {total} file di consegna sono presenti.",
        "en": "All {total} handover files present.",
    },
    # The Italian says "replay" because CONTEXT.md defines Replay as vocabulary
    # the room is taught. Translating it would rename a concept mid-lesson.
    "preflight.recordings.none": {
        "it": "Nessuna registrazione. Un pannello che degrada al replay mostrerà "
              "il suo motivo e nessun output.",
        "en": "No recordings. A degraded pane will show its reason and no output.",
    },
    "preflight.recordings.none.action": {
        "it": "Catturale durante la prova, quando M3 sarà pronto.",
        "en": "Capture during the dry run once M3 lands.",
    },
    "preflight.recordings.ok": {
        "it": "{count} registrazioni su disco.",
        "en": "{count} recordings on disk.",
    },
    "preflight.source.ok": {
        "it": "{role}: {provider} ha risposto come {model}.",
        "en": "{role}: {provider} answered as {model}.",
    },
    "preflight.source.refused": {
        "it": "{role}: {provider} ha rifiutato — {error}",
        "en": "{role}: {provider} refused - {error}",
    },
    "preflight.source.key_stored_call_failed": {
        "it": "La chiave è salvata ma la chiamata è fallita.",
        "en": "The key is stored but the call failed.",
    },
    # Ollama has no key, so "the key is stored" sent a trainer looking for a
    # credential that does not exist.
    "preflight.source.ollama_no_model": {
        "it": "Ollama risponde, ma non per questo modello. Scaricalo, oppure "
              "imposta LLM_MODEL su uno che ha già.",
        "en": "Ollama is answering, but not for this model. Pull it, or set "
              "LLM_MODEL to one it has.",
    },
    # The model ids inside are the provider's own and are never translated.
    "preflight.source.models_hint": {
        "it": "Disponibili secondo l'API: {models}.",
        "en": "Available, per the API: {models}.",
    },
    # The same list, from `model_catalog.FALLBACK_MODELS` rather than from the
    # provider. It says so, because a trainer acting on a stale static list
    # picks a model the API will refuse — while fixing the error that produced
    # this hint.
    "preflight.source.models_hint_fallback": {
        "it": "Elenco di riserva, non dall'API (l'API non ha risposto): "
              "{models}. Da verificare prima di sceglierne uno.",
        "en": "Backstop list, not from the API (the API did not answer): "
              "{models}. Verify before choosing one.",
    },
    "preflight.source.failed": {
        "it": "{role}: {provider} non ha risposto — {error}",
        "en": "{role}: {provider} failed - {error}",
    },
    "preflight.source.no_pane": {
        "it": "{provider} (configurato, nessun pannello)",
        "en": "{provider} (configured, no pane)",
    },
    # ── stage console ─────────────────────────────────────────────────────
    "console.auth.required": {
        "it": "Password della stage console richiesta.",
        "en": "Stage console password required.",
    },
    "console.keys.nothing": {
        "it": "Niente da salvare.",
        "en": "Nothing to save.",
    },
    "console.keys.saved": {
        "it": "Impostazioni salvate: {count}.",
        "en": "Saved {count} setting(s).",
    },
    "console.keys.clear_hint": {
        "it": "Invia il valore letterale CLEAR per azzerare una chiave.",
        "en": "Send the literal value CLEAR to blank a key.",
    },
    "console.keys.cleared": {
        "it": "Chiavi azzerate: {count}.",
        "en": "Cleared {count} key(s).",
    },
    # ── harness routes ────────────────────────────────────────────────────
    "harness.unknown_demo_or_sector": {
        "it": "demo o settore sconosciuto: {what}",
        "en": "unknown demo or sector: {what}",
    },
    "harness.unknown_demo_beat_or_sector": {
        "it": "demo, beat o settore sconosciuto: {what}",
        "en": "unknown demo, beat or sector: {what}",
    },
    # ── run planning ──────────────────────────────────────────────────────
    "runs.unavailable_no_source": {
        "it": "nessuna fonte modello configurata per questo ruolo",
        "en": "no model source configured for this role",
    },
    "runs.not_executable": {
        "it": "{beat_id} non è eseguibile: {reason}",
        "en": "{beat_id} is not executable: {reason}",
    },
    "runs.no_run_block": {
        "it": "nessun run block definito",
        "en": "no run block defined",
    },
    "runs.run_blocks_missing": {
        "it": "Run block mancanti in {path}. Senza di essi Banco non può eseguire "
              "nessun beat; vedi docs/adr/0003.",
        "en": "Run blocks missing at {path}. Banco cannot execute any beat "
              "without them; see docs/adr/0003.",
    },
    "runs.input_escapes_sector": {
        "it": "Il percorso di input esce dalla cartella demo del settore: {path}",
        "en": "Input path escapes the sector demo directory: {path}",
    },
    "runs.input_missing": {
        "it": "File di input mancante: {path}",
        "en": "Input file missing: {path}",
    },
    "runs.pane_fallback_label": {
        "it": "pannello {index}",
        "en": "pane {index}",
    },
    # ── D3's ladder: the sector's documents, and how a pane gets them ─────
    "corpus.escapes_sector": {
        "it": "Cartella dei documenti fuori dal settore: {path}",
        "en": "Document folder outside the sector: {path}",
    },
    "corpus.empty": {
        "it": "Nessun documento da indicizzare per il settore «{sector}».",
        "en": "No documents to index for sector '{sector}'.",
    },
    "corpus.index_missing": {
        "it": "L'indice del settore «{sector}» non è stato costruito. "
              "Costruiscilo dalla console prima della lezione: "
              "python scripts/build_index.py --settore {sector}",
        "en": "The index for sector '{sector}' has not been built. Build it "
              "from the console before the lesson: "
              "python scripts/build_index.py --settore {sector}",
    },
    "corpus.context_heading": {
        "it": "PASSAGGI RECUPERATI DAI DOCUMENTI DELLA CASA:",
        "en": "PASSAGES RETRIEVED FROM THE HOUSE DOCUMENTS:",
    },
    "corpus.all_heading": {
        "it": "DOCUMENTI DELLA CASA, PER INTERO:",
        "en": "THE HOUSE DOCUMENTS, IN FULL:",
    },
    "corpus.no_documents": {
        "it": "Il settore «{sector}» non ha documenti da mettere in contesto.",
        "en": "Sector '{sector}' has no documents to put in context.",
    },
    # ── the handover files a run writes ───────────────────────────────────
    "chain.written_by": {
        "it": "Scritto da Banco a partire da {beat_id} il {stamp}.",
        "en": "Written by Banco from {beat_id} on {stamp}.",
    },
    "chain.overwritten": {
        "it": "Settore: {sector}. Sovrascritto a ogni esecuzione riuscita; "
              "vedi PROJECT.md invariante 3.",
        "en": "Sector: {sector}. Overwritten on a successful run; "
              "see PROJECT.md invariant 3.",
    },
    "chain.produced_by": {
        "it": "{provider} · {model} · temperatura {temperature}",
        "en": "{provider} · {model} · temperature {temperature}",
    },

    # ── network validation ────────────────────────────────────────────────
    # "loopback" stays untranslated in Italian: it is the term the error is
    # about, and a trainer searching for it should find it in either language.
    "network.ollama.empty": {
        "it": "L'indirizzo di Ollama è vuoto.",
        "en": "Ollama base URL is empty.",
    },
    "network.ollama.scheme": {
        "it": "L'indirizzo di Ollama deve usare http o https; trovato lo schema "
              "{scheme} in {url}.",
        "en": "Ollama base URL must use http or https, got {scheme} scheme in {url}.",
    },
    "network.ollama.credentials": {
        "it": "L'indirizzo di Ollama non deve contenere credenziali. Togli la "
              "parte user:password@: Ollama non la usa, e finirebbe scritta in "
              ".env e nei log.",
        "en": "Ollama base URL must not embed credentials. Remove the "
              "user:password@ part; Ollama does not use them, and they would be "
              "written to .env and to logs.",
    },
    "network.ollama.no_host": {
        "it": "L'indirizzo di Ollama non ha un host: {url}.",
        "en": "Ollama base URL has no host: {url}.",
    },
    "network.ollama.not_loopback": {
        "it": "L'indirizzo di Ollama deve puntare a questa macchina; trovato "
              "l'host {host}. Solo loopback (localhost, 127.0.0.1, ::1). Un host "
              "remoto manderebbe ogni prompt fuori da questa macchina.",
        "en": "Ollama base URL must point at this machine, got host {host}. "
              "Loopback only (localhost, 127.0.0.1, ::1). A remote host would "
              "send every prompt off this machine.",
    },
    # ── parameters that did not reach the API ─────────────────────────────
    # Every one of these is rendered beside a pane on the projected surface,
    # in place of the value that pane would otherwise appear to claim. They say
    # what happened and, where a trainer can act on it, what to change. They
    # never say "unsupported" on its own: "this model does not accept it" and
    # "the installed library will not carry it" are different facts with
    # different fixes, and the whole reason `dropped` carries a reason rather
    # than a flag is that the room is entitled to the difference.
    "drop.temperature.sdk_lacks_parameter": {
        "it": "temperatura non inviata: la libreria installata non la accetta "
              "su questa chiamata.",
        "en": "temperature not sent: the installed library does not accept it "
              "on this call.",
    },
    "drop.temperature.model_ignores": {
        "it": "temperatura non inviata: questo modello non la applica.",
        "en": "temperature not sent: this model does not apply it.",
    },
    "drop.temperature.thinking_needs_default": {
        "it": "temperatura non inviata: con un budget di ragionamento attivo "
              "questo modello ammette solo il valore predefinito.",
        "en": "temperature not sent: with a reasoning budget active this model "
              "accepts only its default value.",
    },
    "drop.temperature.reasoning_model": {
        "it": "temperatura non inviata: i modelli di ragionamento non "
              "espongono il campionamento.",
        "en": "temperature not sent: reasoning models do not expose sampling.",
    },
    "drop.max_tokens.sdk_lacks_parameter": {
        "it": "tetto di generazione non inviato: la libreria installata non "
              "accetta nessuno dei due campi.",
        "en": "generation ceiling not sent: the installed library accepts "
              "neither field.",
    },
    "drop.think.sdk_lacks_parameter": {
        "it": "ragionamento non inviato: la libreria installata non lo accetta.",
        "en": "reasoning not sent: the installed library does not accept it.",
    },
    "drop.think.anthropic_takes_a_budget": {
        "it": "ragionamento non inviato: qui è un budget in token, non un "
              "livello. Indica un numero.",
        "en": "reasoning not sent: here it is a token budget, not a level. "
              "State a number.",
    },
    "drop.think.google_takes_a_budget": {
        "it": "ragionamento non inviato: questo modello vuole un budget in "
              "token, non un livello.",
        "en": "reasoning not sent: this model takes a token budget, not a level.",
    },
    "drop.think.google_takes_a_level": {
        "it": "ragionamento non inviato: questo modello vuole un livello, non "
              "un budget in token.",
        "en": "reasoning not sent: this model takes a level, not a token budget.",
    },
    "drop.think.openai_takes_a_level": {
        "it": "ragionamento non inviato: qui è un livello, non un budget in "
              "token.",
        "en": "reasoning not sent: here it is a level, not a token budget.",
    },
    "drop.think.ollama_takes_boolean_or_level": {
        "it": "ragionamento non inviato: Ollama accetta acceso/spento o un "
              "livello, non un budget in token.",
        "en": "reasoning not sent: Ollama accepts on/off or a level, not a "
              "token budget.",
    },
    "drop.think.level_not_offered": {
        "it": "ragionamento non inviato: questo livello non è fra quelli che "
              "il fornitore accetta.",
        "en": "reasoning not sent: this level is not one the provider accepts.",
    },
    "drop.think.model_does_not_deliberate": {
        "it": "ragionamento non inviato: questo modello non ha una modalità di "
              "ragionamento.",
        "en": "reasoning not sent: this model has no reasoning mode.",
    },
    "drop.think.budget_below_minimum": {
        "it": "ragionamento non inviato: il budget è sotto il minimo accettato "
              "(1024 token).",
        "en": "reasoning not sent: the budget is below the accepted minimum "
              "(1024 tokens).",
    },
    "drop.think.budget_not_below_max_tokens": {
        "it": "ragionamento non inviato: il budget deve stare sotto il tetto di "
              "generazione, altrimenti non resta spazio per la risposta.",
        "en": "reasoning not sent: the budget must stay below the generation "
              "ceiling, or there is no room left for an answer.",
    },
    "drop.think.no_off_switch": {
        "it": "ragionamento non disattivato: questo modello non documenta un "
              "modo per spegnerlo.",
        "en": "reasoning not disabled: this model documents no way to turn it "
              "off.",
    },

    # ── the capability check ──────────────────────────────────────────────
    # A warning, never a failure: a trainer may knowingly rehearse on a model
    # that ignores the knob. What it may not do is stay silent, because the
    # demo it describes runs, reads correctly and teaches nothing.
    "preflight.capability.not_carried": {
        "it": "{demo}: nessuna fonte collegata invia «{parameter}», che è il "
              "parametro su cui si regge {beat}. Il beat gira lo stesso e non "
              "dimostra niente.",
        "en": "{demo}: no bound source sends “{parameter}”, which is the "
              "parameter {beat} rests on. The beat still runs and demonstrates "
              "nothing.",
    },
    "preflight.capability.alternatives": {
        "it": "Lo invierebbero: {sources}.",
        "en": "These would send it: {sources}.",
    },
    "preflight.capability.no_alternative": {
        "it": "Nessuna fonte configurata su questa macchina lo invia.",
        "en": "No source configured on this machine sends it.",
    },

    # ── session profiles ──────────────────────────────────────────────────
    # Returned as the body of a 422 from the console, so each one names the
    # field: a trainer has to be able to fix the file from the message.
    "sessions.not_an_object": {
        "it": "Il profilo {name} non è un oggetto JSON.",
        "en": "Profile {name} is not a JSON object.",
    },
    "sessions.bad_version": {
        "it": "Il profilo {name} dichiara version {found}; atteso {expected}.",
        "en": "Profile {name} declares version {found}; expected {expected}.",
    },
    "sessions.bad_name": {
        "it": "Nome di profilo non valido: {name}. Lettere, cifre, punto, "
              "trattino e trattino basso, massimo 64 caratteri.",
        "en": "Invalid profile name: {name}. Letters, digits, dot, hyphen and "
              "underscore, at most 64 characters.",
    },
    "sessions.missing": {
        "it": "Nessun profilo di sessione {name} in {path}.",
        "en": "No session profile {name} at {path}.",
    },
    "sessions.unparseable": {
        "it": "Il profilo {name} non è JSON leggibile: {detail}",
        "en": "Profile {name} is not readable JSON: {detail}",
    },
    "sessions.credential_shaped": {
        "it": "Il campo {field} ha la forma di una credenziale. I profili sono "
              "versionati e letti ad alta voce: le chiavi restano in .env.",
        "en": "Field {field} is credential-shaped. Profiles are committed and "
              "read aloud; keys stay in .env.",
    },
    "sessions.roles_not_an_object": {
        "it": "{where} non è un oggetto.",
        "en": "{where} is not an object.",
    },
    "sessions.role_not_an_object": {
        "it": "{where} non è un oggetto {{provider, model, params}}.",
        "en": "{where} is not a {{provider, model, params}} object.",
    },
    "sessions.unknown_role": {
        "it": "{where} nomina ruoli sconosciuti: {roles}. Ruoli validi: {known}.",
        "en": "{where} names unknown roles: {roles}. Valid roles: {known}.",
    },
    "sessions.unknown_provider": {
        "it": "{where} nomina un fornitore sconosciuto: {provider}.",
        "en": "{where} names an unknown provider: {provider}.",
    },
    "sessions.model_not_a_string": {
        "it": "{where}.model deve essere una stringa.",
        "en": "{where}.model must be a string.",
    },
    "sessions.bad_params": {
        "it": "{where}.params non è valido: {detail}",
        "en": "{where}.params is not valid: {detail}",
    },
    "sessions.unknown_demo": {
        "it": "Il profilo {name} nomina moduli inesistenti: {demos}. "
              "Moduli validi: {known}.",
        "en": "Profile {name} names demos that do not exist: {demos}. "
              "Valid demos: {known}.",
    },

    # ── configuration ─────────────────────────────────────────────────────
    "config.env.line_break": {
        "it": "Rifiuto di scrivere {key}: il valore contiene un a capo o un byte "
              "nullo, che definirebbe un'altra variabile in .env.",
        "en": "Refusing to write {key}: the value contains a line break or null "
              "byte, which would define another variable in .env.",
    },
}

# -*- coding: utf-8 -*-
"""Production-software house for knitwear — sector module.

The record is a **scheda di specifica**: a customer request turned into a
functional specification for the house's own production-management software.
The internal specification scale (SP-1…SP-5) and the house rules are invented
on purpose.

What makes this sector's M3 ladder its own, and not a repeat of the automation
or DeFi packs, is *what the scale measures*. Ask an ungrounded model how
software requests are classified and it answers with the industry average —
MoSCoW, story points, a priority/severity matrix, Given/When/Then acceptance
criteria. All of that measures **priority and size**. The SP scale measures
something no framework measures: how much specification the request is still
missing, and who has to sign it. And it has a level — SP-5 — that says the
request must not become a ticket at all, because it is a change to the
customer's process and not to the software. No priority framework has that
level, so no model can guess it.

The second thing a model cannot check, and fills anyway, is the shop-floor
number: the standard time of a phase. It will offer a confident industry figure
in minutes per garment. The house rule says a time that was not measured on the
floor is written «dichiarato, non rilevato» — which is the whole argument of
this trade in one field.

Two records are placed deliberately, and both are documented here so that a
seed change cannot silently break the demo:

* **Row 5 is the only SP-5.** DEMO-CHECKLIST failure #2 lowers row 5 of the D4
  table by one level, so the table presents a request that must not be built at
  all as merely «sospesa». That is the error that costs this trade money, so it
  is the one the failure should land on.
* **Row 7 is the D1/D4 record.** It is SP-4 with *measured* process data and
  unusable acceptance criteria: the raw notes contain everything needed except
  the rule, so the model that drafts from them guesses SP-1 or SP-2. Leaving
  that to chance lets the raw notes and the ground truth disagree.
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..common import (as_json, esc, five_attributes_md, pick_tradeoff,
                      standard_house_docs, three_candidates_md)

SECTOR = {
    "id": "maglieria",
    "label": "Software house gestionale per la maglieria",
    "records_dir": "specifiche",
    "poison_dir": "avvelenata",
    "record_noun": "schede di specifica",
    "file_stem": "specifica",
    "ground_truth_cols": [
        "number", "reference", "customer_code", "customer_kind", "module",
        "module_version", "module_ref", "channel", "request_date", "area",
        "phase", "process_data", "survey_ref", "phase_std_min",
        "criteria_count", "data_impact", "scope_kind", "estimate_days",
        "grade", "capi_month", "operators_affected", "days_queued",
        "reviewer_signed", "customer_approval", "outcome_certain", "operator",
    ],
}

CHANNELS = ["telefono", "posta elettronica", "visita in reparto",
            "portale assistenza"]

# The three states the house recognises. Only the first one lets a time be
# written as a number.
PROCESS_DATA = ["rilevati", "dichiarati", "non disponibili"]

DATA_IMPACT = ["nessuno", "nuovo campo", "modifica di record già in produzione"]

# The reparto the D1/D4 record sits in, by index into config["reparti"].
# Pinned so the four invented values in generate_chain.py's CHAIN block stay
# coherent with the record they are the wrong answers to. Rimaglio is the
# knitwear phase every maker watches, and "avanzamento del rimaglio per
# commessa e per addetto" is the most ordinary request in the trade.
DEMO_REPARTO = 3

NOTES_UNCERTAIN = [
    "Tempo di fase riferito a voce dal capo reparto e non rilevato: DA VERIFICARE.",
    "Versione in esercizio del modulo non confermata dal committente: DA VERIFICARE.",
    "Criteri di accettazione raccolti in chiamata e non rivisti per iscritto: DA VERIFICARE.",
]
NOTES_PLAIN = [
    "Nessun rilievo in sede di revisione della specifica.",
    "Allegato il verbale della chiamata con il committente.",
    "Confermata la versione in esercizio sull'installato del committente.",
    "Richiesta già presentata in forma diversa nel ciclo precedente.",
    "",
]


@dataclass
class Specifica:
    number: int
    reference: str
    customer_code: str
    customer_kind: str
    module: str
    module_version: str
    module_ref: str
    channel: str
    request_date: str
    area: str
    phase: str
    request: str
    process_data: str
    survey_ref: str
    phase_std_min: str
    criteria_count: int
    data_impact: str
    scope_kind: str
    estimate_days: str
    grade: str
    grade_label: str
    reviewer_signed: bool
    customer_approval: bool
    outcome_certain: bool
    operator: str
    notes: str = ""
    capi_month: int = 0
    operators_affected: int = 0
    days_queued: int = 0
    tags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


# One record per target class, so all five levels of the invented scale appear
# in twelve sheets. The attributes are then sampled to MATCH the class and the
# class is re-derived from them by _classify: the sheets stay internally
# consistent, which is what lets the expert recompute a class by hand in D4.
CLASS_PLAN = [0, 0, 1, 1, 1, 1, 2, 2, 2, 3, 3, 4]

# The two reserved rows, 1-based, and what they are reserved for. See the module
# docstring: both are demo mechanics, not data properties.
ROW_FAILURE = 5      # the only SP-5 — DEMO-CHECKLIST failure #2 lands here
ROW_DEMO = 7         # the record D1's raw notes describe, and D4 re-reads


def _classify(scope_kind: str, data_impact: str, process_data: str) -> int:
    """The house rule, written once. Highest applicable level wins.

    Three fields, in this order, and nothing else: a reviewer recomputes a class
    by hand in ten seconds, which is exactly what D4's verification step needs.
    """
    if scope_kind == "processo":
        return 4
    if data_impact == "modifica di record già in produzione":
        return 3
    if process_data != "rilevati":
        return 2
    if data_impact == "nuovo campo":
        return 1
    return 0


def _attributes(target: int, rng: random.Random) -> tuple[str, str, str]:
    """Sample scope, data impact and process-data state consistent with `target`."""
    if target == 4:
        return "processo", rng.choice(DATA_IMPACT[:2]), rng.choice(PROCESS_DATA)
    if target == 3:
        # SP-4 is driven by the data impact alone, so the process data can be
        # anything — but most of these have been measured, otherwise the sheet
        # would read as if only unmeasured requests ever touch production.
        return ("software", "modifica di record già in produzione",
                rng.choice(["rilevati", "rilevati", "rilevati", "dichiarati"]))
    if target == 2:
        return ("software", rng.choice(DATA_IMPACT[:2]),
                rng.choice(["dichiarati", "dichiarati", "non disponibili"]))
    if target == 1:
        return "software", "nuovo campo", "rilevati"
    return "software", "nessuno", "rilevati"


def _plan(count: int, rng: random.Random) -> list[int]:
    """The class of each of the twelve sheets, with the two reserved rows set."""
    plan = CLASS_PLAN[:count] or [0]
    while len(plan) < count:
        plan.append(1)
    rng.shuffle(plan)

    def place(index: int, value: int) -> None:
        """Put `value` at `index`, swapping out whatever was there."""
        if index >= len(plan) or plan[index] == value:
            return
        donor = next((i for i, v in enumerate(plan)
                      if v == value and i not in (ROW_FAILURE - 1, ROW_DEMO - 1)), None)
        if donor is None:
            donor = next((i for i, v in enumerate(plan) if v == value), None)
        if donor is None:
            plan[index] = value
            return
        plan[index], plan[donor] = plan[donor], plan[index]

    place(ROW_FAILURE - 1, 4)   # the only SP-5 is the row failure #2 lowers
    place(ROW_DEMO - 1, 3)      # the record D1 drafts from is SP-4
    return plan


def build_records(config: dict, rng: random.Random) -> list[Specifica]:
    period, grades, operators = config["sale"], config["grades"], config["operators"]
    committenti, reparti = config["committenti"], config["reparti"]
    processo = config["richieste_processo"]
    year = period["date"][:4]
    plan = _plan(period["lot_count"], rng)

    out: list[Specifica] = []
    for n, target in enumerate(plan, start=1):
        scope_kind, data_impact, process_data = _attributes(target, rng)
        if n == ROW_DEMO:
            # The demo record: measured data, so the true phase time exists and
            # can be checked; unusable criteria, so the estimate must be blank.
            process_data = "rilevati"
        idx = _classify(scope_kind, data_impact, process_data)
        g = grades[idx]
        # Reparto, fase, modulo and request travel together: a shop-floor
        # request filed against the wrong module is the first thing someone who
        # does this daily notices.
        if scope_kind == "processo":
            src = rng.choice(processo)
            request = src["richiesta"]
        else:
            src = reparti[DEMO_REPARTO] if n == ROW_DEMO else rng.choice(reparti)
            request = rng.choice(src["richieste"])
        area, phase, module = src["area"], src["fase"], src["modulo"]
        # The phase time always comes from the reparto it belongs to, including
        # for a process request, which is filed against a reparto like any other.
        lo_min, hi_min = next((r["min_capo"] for r in reparti if r["fase"] == phase),
                              (1.0, 6.0))
        version = f"v{rng.randint(2, 5)}.{rng.randint(0, 9)}"
        criteria = rng.choice([0, 1, 2, 2, 3, 3, 4])
        if n == ROW_DEMO:
            criteria = 1
        certain = rng.random() > 0.3
        std_min = (f"{rng.uniform(lo_min, hi_min):.2f}".replace(".", ",")
                   if process_data == "rilevati" else "NON RILEVATO")
        lo = rng.randint(1, 9)
        # An SP-5 never carries an estimate: house rule 6 says it does not
        # become a ticket, so there is nothing to size.
        estimate = ("NON STIMABILE"
                    if scope_kind == "processo" or criteria < 2
                    or process_data != "rilevati"
                    else f"{lo}–{lo + rng.randint(1, 5)}")
        out.append(Specifica(
            number=n,
            reference=f"SPEC-{year}-{n:03d}",
            customer_code=f"CLI-{rng.randint(1, 48):03d}",
            customer_kind=rng.choice(committenti),
            module=module,
            module_version=version,
            module_ref=f"{module} {version}",
            channel=rng.choice(CHANNELS),
            request_date=f"{year}-09-{rng.randint(1, 11):02d}",
            area=area,
            phase=phase,
            request=request,
            process_data=process_data,
            survey_ref=(f"RIL-{year}-{rng.randint(1, 60):03d}"
                        if process_data == "rilevati" else "RILEVAZIONE NON ESEGUITA"),
            phase_std_min=std_min,
            criteria_count=criteria,
            data_impact=data_impact,
            scope_kind=scope_kind,
            estimate_days=estimate,
            grade=g["code"], grade_label=g["label"],
            reviewer_signed=rng.random() > 0.35,
            customer_approval=rng.random() > 0.45,
            outcome_certain=certain,
            operator=rng.choice(operators),
            notes=(rng.choice(NOTES_PLAIN) if certain else rng.choice(NOTES_UNCERTAIN)),
            capi_month=rng.choice([180, 340, 520, 700, 950, 1200, 1800, 2400]),
            operators_affected=rng.randint(1, 14),
            days_queued=rng.randint(0, 34),
        ))
    return out


TEXTS = {
    "rules_title": "Standard interno di specifica e accettazione",
    "rules_subtitle": "Edizione in vigore per le richieste dei committenti. San Marino.",
    "scale_section": "Scala interna di specifica",
    "scale_intro": ("La casa adotta una scala interna a cinque livelli, denominata "
                    "<b>scala SP</b>, assegnata a ogni richiesta prima che entri in stima. "
                    "La scala non misura né la priorità né la dimensione del lavoro: misura "
                    "<b>quanta specifica manca ancora alla richiesta e chi deve firmarla</b>. "
                    "Non equivale a MoSCoW, ai punti storia né ad alcuna matrice "
                    "priorità/gravità, e ogni conversione richiede il parere del revisore "
                    "che firma la specifica."),
    "fields_section": "Campi obbligatori in ogni scheda di specifica",
    "fields_intro": ("Nessuna scheda può essere chiusa se manca anche uno solo dei campi "
                     "seguenti:"),
    "responsibility": ("La responsabilità finale della specifica resta in capo al revisore "
                       "che la firma. Strumenti automatici possono produrre bozze, mai schede "
                       "chiuse: un modulo, una versione in esercizio, un tempo di fase o un "
                       "codice cliente prodotti da un assistente valgono come proposta, non "
                       "come dato."),
    "guide_title": "Guida rapida alla scala SP",
    "guide_intro": ("Si leggono tre campi, in quest'ordine: ambito dell'intervento, impatto "
                    "sul modello dati, stato dei dati di processo. Il primo che si applica "
                    "decide la classe. In caso di dubbio fra due livelli adiacenti si assegna "
                    "sempre il livello <b>più alto</b>, cioè il più prudente, e il dubbio va "
                    "annotato nel campo note."),
    "common_errors": [
        "Assegnare SP-1 quando il tempo di fase è stato riferito a voce e non rilevato: un dato dichiarato porta la scheda a SP-3, qualunque sia l'impatto sul modello dati.",
        "Usare SP-5 come sinonimo di «richiesta rifiutata»: SP-5 dice che l'intervento non è software, non che non vada fatto.",
        "Confondere NON DEFINITI con SP-3: i criteri di accettazione mancanti bloccano la stima, non la classe.",
        "Assegnare SP-2 a una modifica di record già in produzione perché «è solo un campo»: toccare dati esistenti è SP-4.",
        "Scrivere il nome del maglificio al posto del codice cliente perché «tanto è una bozza interna»: la bozza è il documento che poi viene allegato.",
    ],
}


def build_house_docs(config: dict, out_dir: Path) -> list[Path]:
    return standard_house_docs(config, out_dir, TEXTS,
                               "standard-specifica", "guida-scala-specifica")


def record_blocks(r: Specifica, config: dict):
    period = config["sale"]
    return [
        ("title", f"Specifica {r.number:03d} — {esc(r.module)}"),
        ("subtitle", f"{esc(period['code'])} — {esc(period['title'])} · {period['date']}"),
        ("field", f"<b>Riferimento specifica</b>: {esc(r.reference)}"),
        ("field", f"<b>Codice cliente</b>: {esc(r.customer_code)} — <b>tipo di committente</b>: {esc(r.customer_kind)}"),
        ("field", f"<b>Modulo del gestionale</b>: {esc(r.module)} — <b>versione in esercizio</b>: {esc(r.module_version)}"),
        ("field", f"<b>Canale di arrivo</b>: {esc(r.channel)} — <b>data della richiesta</b>: {r.request_date}"),
        ("field", f"<b>Reparto</b>: {esc(r.area)} — <b>fase</b>: {esc(r.phase)}"),
        ("field", f"<b>Richiesta</b>: {esc(r.request)}"),
        ("spacer", "8"),
        ("h2", "Dati di processo"),
        ("field", f"<b>Stato dei dati di processo</b>: {esc(r.process_data)}"),
        ("field", f"<b>Riferimento della rilevazione</b>: {esc(r.survey_ref)}"),
        ("field", f"<b>Tempo standard della fase</b>: {esc(r.phase_std_min)}"
                  + (" min/capo" if r.phase_std_min != "NON RILEVATO" else "")),
        ("field", f"<b>Capi al mese interessati</b>: {r.capi_month}"),
        ("field", f"<b>Addetti del reparto impattati</b>: {r.operators_affected}"),
        ("spacer", "8"),
        ("h2", "Requisito"),
        ("field", f"<b>Criteri di accettazione misurabili</b>: "
                  + (str(r.criteria_count) if r.criteria_count >= 2 else "NON DEFINITI")),
        ("field", f"<b>Impatto sul modello dati</b>: {esc(r.data_impact)}"),
        ("field", f"<b>Ambito dell'intervento</b>: {esc(r.scope_kind)}"),
        ("field", f"<b>Stima</b>: {esc(r.estimate_days)}"
                  + (" giornate-uomo" if r.estimate_days != "NON STIMABILE" else "")),
        ("field", f"<b>Giorni in coda dalla richiesta</b>: {r.days_queued}"),
        ("field", f"<b>Classe di specifica</b>: {esc(r.grade)} ({esc(r.grade_label)})"),
        ("spacer", "8"),
        ("h2", "Verifica e firme"),
        ("field", "Esito della revisione confermato."
                  if r.outcome_certain else "ESITO NON CONFERMATO"),
        ("field", f"Firma del revisore: {esc(r.operator)}"),
        ("field", "Secondo revisore: firma acquisita."
                  if r.reviewer_signed else "SECONDO REVISORE ASSENTE"),
        # Required only from SP-4 up, so the habitual blank appears exactly
        # where the rulebook says it matters — and D4 can be checked on it.
        ("field", "Approvazione scritta del committente: non richiesta a questa classe."
                  if r.grade in ("SP-1", "SP-2", "SP-3")
                  else ("Approvazione scritta del committente: acquisita."
                        if r.customer_approval else "APPROVAZIONE CLIENTE ASSENTE")),
        ("field", esc(r.notes) if r.notes else "—"),
        ("spacer", "10"),
        ("body", f"<font size=8 color='#6b7788'>Scheda redatta da {esc(r.operator)} — bozza non firmata.</font>"),
    ]


def poison_record(records: list[Specifica], config: dict) -> Specifica:
    """The sheet that carries the hidden instruction.

    Its cover story is the one that actually happens to a software house: the
    customer writes their own «specification» and sends it in. It arrives
    through the same channel as the real work, which is the whole point of M5.
    """
    n = config["poison"]["lot_number"]
    year = config["sale"]["date"][:4]
    return Specifica(
        number=n, reference=f"SPEC-{year}-{n:03d}",
        customer_code="CLI-000", customer_kind="maglificio conto terzi",
        module="Avanzamento di reparto", module_version="NON DETERMINATA",
        module_ref="Avanzamento di reparto NON DETERMINATA",
        channel="posta elettronica", request_date=f"{year}-09-10",
        area="Rimaglio", phase="rimaglio manuale dei pannelli",
        request="riportare l'avanzamento del rimaglio come nel foglio allegato dal committente",
        process_data="dichiarati", survey_ref="RILEVAZIONE NON ESEGUITA",
        phase_std_min="NON RILEVATO", criteria_count=0,
        data_impact="nuovo campo", scope_kind="software",
        estimate_days="NON STIMABILE",
        grade="SP-3", grade_label=config["grades"][2]["label"],
        reviewer_signed=False, customer_approval=False, outcome_certain=False,
        operator="—",
        notes="Scheda ricevuta dal committente e acquisita senza revisione.",
        capi_month=640, operators_affected=5, days_queued=2,
    )


def _hearsay(measured: str) -> int:
    """What the capo reparto says the phase takes, rounded to five minutes.

    Deliberately below the measured figure and deliberately round. The three
    numbers the room ends up looking at — what the model invents, what the
    shop floor says, what the survey measured — are three different numbers,
    and house rule 2 exists because the last two disagree.
    """
    try:
        value = float(measured.replace(",", "."))
    except ValueError:
        return 10
    return max(5, int(round(value * 0.62 / 5.0)) * 5)


def demo_files(records: list[Specifica], config: dict) -> dict[str, str]:
    pick = next((r for r in records if r.outcome_certain), records[0])
    five = five_attributes_md(
        f"Specifica {pick.number:03d} — cinque attributi",
        [("Modulo e versione in esercizio", pick.module_ref),
         ("Reparto e fase", f"{pick.area} — {pick.phase}"),
         ("Stato dei dati di processo", pick.process_data),
         ("Impatto sul modello dati", pick.data_impact),
         ("Criteri di accettazione misurabili",
          str(pick.criteria_count) if pick.criteria_count >= 2 else "NON DEFINITI"),
         ("Classe di specifica", f"{pick.grade} ({pick.grade_label})")],
        "Da incollare al posto di `[INCOLLA 5 ATTRIBUTI]` in `m2-p1`.",
    )
    cands = pick_tradeoff(
        records,
        [lambda r: r.capi_month,                          # most garments touched
         lambda r: (r.operators_affected, r.capi_month),  # most people on the floor
         lambda r: (r.days_queued, r.capi_month)],        # longest waiting
        lambda r: (r.capi_month, r.operators_affected, r.days_queued))
    three = three_candidates_md(
        "Tre specifiche per l'unico slot di sviluppo della settimana",
        "Da mostrare con `m2-p2`. I tre criteri sono quelli che il prompt nomina.",
        ["Capi al mese interessati", "Addetti impattati", "Giorni in coda"],
        [{"label": f"{r.reference} — {r.area.lower()}, {r.module.lower()}",
          "Capi al mese interessati": str(r.capi_month),
          "Addetti impattati": str(r.operators_affected),
          "Giorni in coda": str(r.days_queued)} for r in cands],
    )
    # The D1/D4 record. ROW_DEMO is reserved for it, so this lookup should never
    # fall through — the fallbacks exist so a changed lot_count degrades instead
    # of crashing.
    raw = next((r for r in records
                if r.number == ROW_DEMO and r.grade == "SP-4"
                and r.process_data == "rilevati"),
               next((r for r in records
                     if r.grade == "SP-4" and r.process_data == "rilevati"),
                    records[min(6, len(records) - 1)]))
    grezzi_md = "\n".join([
        f"Specifica {raw.reference} — committente {raw.customer_kind}",
        "",
        f"richiesta arrivata per {raw.channel} il {raw.request_date}",
        f"reparto: {raw.area} — fase: {raw.phase}",
        f"chiedono di {raw.request}",
        "modulo interessato e versione in esercizio: ?",
        "codice cliente: ?",
        f"rilevazione in reparto fatta a luglio, riferimento {raw.survey_ref}",
        "tempo standard della fase: ? (c'è nella rilevazione, non l'ho riportato)",
        f"il capo reparto dice «siamo intorno ai {_hearsay(raw.phase_std_min)} minuti a "
        f"capo» — riferito a voce",
        f"capi al mese sulla commessa: {raw.capi_month}",
        f"addetti del reparto impattati: {raw.operators_affected}",
        "va sistemato anche sulle commesse già chiuse dell'anno, altrimenti i totali non tornano",
        "criteri di accettazione: «deve essere più veloce di adesso» — da riformulare",
        f"giorni in coda dalla richiesta: {raw.days_queued}",
        "classe di specifica: da assegnare",
        "",
    ])
    grezzi_json = as_json({
        "specifica": raw.reference,
        "committente": raw.customer_kind,
        "reparto_e_fase": f"{raw.area} — {raw.phase}",
        "richiesta": raw.request,
        "capi_al_mese": raw.capi_month,
        "addetti_impattati": raw.operators_affected,
        "modulo_e_versione": None,
        "codice_cliente": None,
        "tempo_standard_fase": None,
        "classe_di_specifica": None,
        "rilevazione": raw.survey_ref,
        "dato_riferito_a_voce": f"circa {_hearsay(raw.phase_std_min)} minuti a capo, "
                                f"detto dal capo reparto",
        "da_sistemare_anche": "le commesse già chiuse dell'anno",
        "criteri_accettazione": "«deve essere più veloce di adesso» — da riformulare",
        "giorni_in_coda": raw.days_queued,
    })
    return {"m2-cinque-attributi.md": five, "m2-tre-candidati.md": three,
            "m4-grezzi.md": grezzi_md, "m4-grezzi.json": grezzi_json}

# -*- coding: utf-8 -*-
"""Trade association / business-services desk — sector module.

The record is a member-query sheet: what an associate asked, what was answered,
under which source, and how much verification the answer needed before it left
the office. The internal response scale (UA-1…UA-5) and the house rules are
invented on purpose.

What makes this sector's M3 ladder the sharpest of the set is jurisdiction. Ask
an ungrounded model about notice periods, probation, fixed-term contracts or
licensing and it answers with *Italian* law — fluent, competent, and the wrong
country. The house rulebook says the opposite: cite the San Marino source or
write NON DETERMINATO. The room does not need to know anything about AI to see
the difference; it needs to know where it lives.

The legislative references in the config are REAL and taken from the
association's own public list of laws; the cases, the protocol numbers, the
scale and the rulebook are invented. See LEGGIMI-SINTETICO.md.
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..common import (as_json, esc, five_attributes_md, pick_tradeoff,
                      standard_house_docs, three_candidates_md)

SECTOR = {
    "id": "associazione",
    "label": "Associazione di categoria — sportello agli associati",
    "records_dir": "quesiti",
    "poison_dir": "avvelenata",
    "record_noun": "schede quesito",
    "file_stem": "quesito",
    "ground_truth_cols": [
        "number", "reference", "member_sector", "category", "channel",
        "norm_ref", "contract_ref", "grade", "escalation", "deadline_days",
        "members_affected", "open_days", "answered_in_writing",
        "outcome_certain", "operator",
    ],
}

# The trades on the association's own board, so the room recognises itself.
MEMBER_SECTORS = ["acconciatura", "estetica e benessere", "metalmeccanica",
                  "legno e arredamento", "edilizia", "impiantistica",
                  "autoriparazione", "panificazione", "grafica e stampa"]

CHANNELS = ["sportello", "sportello", "telefono", "posta elettronica"]

ESCALATIONS = ["sportello", "consulente del lavoro", "commercialista",
               "legale esterno", "ufficio competente"]

NOTES_UNCERTAIN = [
    "Fonte sammarinese non reperita in sede di riscontro: DA VERIFICARE.",
    "Contratto collettivo applicabile non confermato dall'associato: DA VERIFICARE.",
    "Riscontro dato a voce e non protocollato lo stesso giorno: DA VERIFICARE.",
]
NOTES_PLAIN = ["Nessun rilievo in fase di riscontro.",
               "Inviata copia della circolare in vigore.",
               "Quesito ricorrente: già trattato in circolare.",
               "Associato richiamato per completare la documentazione.", ""]


@dataclass
class Quesito:
    number: int
    reference: str
    member_sector: str
    category: str
    channel: str
    subject: str
    norm_ref: str
    contract_ref: str
    grade: str
    grade_label: str
    escalation: str
    deadline_days: int
    members_affected: int
    open_days: int
    answered_in_writing: bool
    outcome_certain: bool
    operator: str
    notes: str = ""
    tags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


# One record per target class, so all five levels of the invented scale appear
# in twelve sheets, and so that "Lavoro e occupazione" — the category that makes
# the wrong-jurisdiction answer land — is the most frequent, as it is at a real
# desk. The class is then DERIVED from the flags by _classify: the sheets stay
# internally consistent and the secretary can recompute a class by hand.
CLASS_PLAN = [0, 0, 1, 1, 1, 1, 2, 2, 2, 3, 3, 4]


def _classify(contentious: bool, found: bool, needs_pro: bool,
              written: bool) -> int:
    """The house rule, written once. Jurisdiction first: no source, no answer."""
    if contentious:
        return 4
    if not found:
        return 3
    if needs_pro:
        return 2
    return 1 if written else 0


def build_records(config: dict, rng: random.Random) -> list[Quesito]:
    period, grades, operators = config["sale"], config["grades"], config["operators"]
    categories = config["categorie"]
    # Weighted cycle: "peso" in the config says how often a category really
    # turns up at the desk, so labour and licensing dominate as they do in life.
    ordinary = [c for c in categories
                if not c.get("contenzioso") and not c.get("consulente")
                for _ in range(c.get("peso", 1))]
    professional = [c for c in categories if c.get("consulente")
                    for _ in range(c.get("peso", 1))]
    contentious = [c for c in categories if c.get("contenzioso")]
    plan = CLASS_PLAN[:period["lot_count"]] or [0]
    while len(plan) < period["lot_count"]:
        plan.append(1)
    rng.shuffle(plan)
    # DEMO-CHECKLIST failure #2 lowers row 5 by one level; UA-1 has nothing
    # below it, so row 5 must not be UA-1.
    if plan[4] == 0:
        swap = next((i for i, v in enumerate(plan) if v != 0), 4)
        plan[4], plan[swap] = plan[swap], plan[4]

    out: list[Quesito] = []
    cursor = 0
    pro_cursor = 0
    for n, target in enumerate(plan, start=1):
        if target == 4 and contentious:
            cat, found, needs_pro, written = contentious[0], False, False, False
        elif target == 2 and professional:
            cat, found, needs_pro, written = (professional[pro_cursor % len(professional)],
                                              True, True, True)
            pro_cursor += 1
        else:
            cat = ordinary[cursor % len(ordinary)]
            cursor += 1
            needs_pro = False
            found = target != 3
            written = target == 1
        idx = _classify(bool(cat.get("contenzioso")), found,
                        bool(cat.get("consulente")), written)
        g = grades[idx]
        # Quesito and source are paired by position in the config, so the cited
        # law actually fits the question asked. A board of artisans reads the
        # pairing before it reads anything else.
        norms = cat.get("norme", [])
        j = rng.randrange(len(cat["quesiti"]))
        norm = norms[j % len(norms)] if (found and norms) else "NON DETERMINATO"
        certain = rng.random() > 0.3
        sector_it = rng.choice(MEMBER_SECTORS)
        out.append(Quesito(
            number=n,
            reference=f"PRO-{period['date'][:4]}-{n:03d}",
            member_sector=sector_it,
            category=cat["nome"],
            channel=rng.choice(CHANNELS),
            subject=cat["quesiti"][j],
            norm_ref=norm,
            contract_ref=(f"contratto collettivo di categoria in vigore — {sector_it}"
                          if rng.random() > 0.15 else "NON DETERMINATO"),
            grade=g["code"], grade_label=g["label"],
            escalation=(ESCALATIONS[0] if idx == 0 else
                        ESCALATIONS[1] if idx == 1 else
                        ESCALATIONS[2] if idx == 2 else
                        ESCALATIONS[4] if idx == 3 else ESCALATIONS[3]),
            deadline_days=rng.choice([5, 10, 15, 20, 30, 30, 45]),
            members_affected=rng.choice([1, 1, 2, 4, 9, 18, 40, 75]),
            open_days=rng.randint(0, 24),
            answered_in_writing=written,
            outcome_certain=certain,
            operator=rng.choice(operators),
            notes=(rng.choice(NOTES_PLAIN) if certain else rng.choice(NOTES_UNCERTAIN)),
        ))
    return out


TEXTS = {
    "rules_title": "Regolamento interno di riscontro ai quesiti degli associati",
    "rules_subtitle": "Edizione in vigore per lo sportello. Repubblica di San Marino.",
    "scale_section": "Scala interna di classe di riscontro",
    "scale_intro": ("L'associazione adotta una scala interna a cinque livelli, denominata "
                    "<b>scala UA</b>, assegnata a ogni quesito prima che la risposta esca "
                    "dall'ufficio. La scala non misura la difficoltà del quesito: misura "
                    "<b>quanta verifica serve, e chi può firmare la risposta</b>. Nessuna "
                    "conversione con scale di altre associazioni è ammessa."),
    "fields_section": "Campi obbligatori in ogni scheda quesito",
    "fields_intro": ("Nessun riscontro scritto può essere inviato se manca anche uno solo dei "
                     "campi seguenti:"),
    "responsibility": ("La responsabilità del riscontro resta in capo a chi lo firma e, per le "
                       "classi UA-3 e superiori, al professionista che lo ha validato. "
                       "Strumenti automatici possono produrre bozze, mai riscontri inviati: "
                       "una fonte normativa prodotta da un assistente vale come traccia da "
                       "verificare, non come citazione."),
    "guide_title": "Guida rapida alla scala UA",
    "guide_intro": ("In caso di dubbio fra due livelli adiacenti si assegna sempre il livello "
                    "<b>più alto</b>, cioè quello che richiede più verifica. Il dubbio va "
                    "annotato nel campo note."),
    "common_errors": [
        "Assegnare UA-1 perché il quesito è semplice: la classe dipende dalla fonte citata e da chi firma, non dalla difficoltà.",
        "Citare una norma italiana perché la fattispecie è analoga: se la fonte sammarinese non è stata reperita la classe è UA-4, non UA-2.",
        "Riportare a memoria un importo o una tabella salariale invece di allegare quella in vigore.",
        "Trascrivere per esteso i dati personali dell'associato o dei suoi dipendenti nella scheda.",
        "Chiudere come UA-2 un quesito su un contenzioso già aperto: è sempre UA-5.",
    ],
}


def build_house_docs(config: dict, out_dir: Path) -> list[Path]:
    return standard_house_docs(config, out_dir, TEXTS,
                               "regolamento-riscontro", "guida-scala-riscontro")


def record_blocks(q: Quesito, config: dict):
    period = config["sale"]
    return [
        ("title", f"Quesito {q.number:03d} — {esc(q.category)}"),
        ("subtitle", f"{esc(period['code'])} — {esc(period['title'])} · {period['date']}"),
        ("field", f"<b>Protocollo</b>: {esc(q.reference)}"),
        ("field", f"<b>Associato</b>: settore {esc(q.member_sector)} (dati anagrafici non trascritti)"),
        ("field", f"<b>Canale</b>: {esc(q.channel)}"),
        ("field", f"<b>Oggetto</b>: {esc(q.subject)}"),
        ("field", f"<b>Riferimento normativo citato</b>: {esc(q.norm_ref)}"),
        ("field", f"<b>Contratto collettivo applicabile</b>: {esc(q.contract_ref)}"),
        ("spacer", "8"),
        ("h2", "Riscontro"),
        ("field", f"<b>Classe di riscontro</b>: {esc(q.grade)} ({esc(q.grade_label)})"),
        ("field", f"<b>Passato a</b>: {esc(q.escalation)}"),
        ("field", f"<b>Termine di riscontro</b>: {q.deadline_days} giorni"),
        ("field", f"<b>Giorni di giacenza</b>: {q.open_days}"),
        ("field", f"<b>Associati potenzialmente interessati</b>: {q.members_affected}"),
        ("field", "Riscontro scritto inviato."
                  if q.answered_in_writing else "RISCONTRO SCRITTO NON INVIATO"),
        ("spacer", "8"),
        ("h2", "Verifica e firme"),
        ("field", "Riscontro confermato da chi lo ha redatto."
                  if q.outcome_certain else "RISCONTRO NON CONFERMATO"),
        ("field", f"Firma: {esc(q.operator)}"),
        ("field", esc(q.notes) if q.notes else "—"),
        ("spacer", "10"),
        ("body", f"<font size=8 color='#6b7788'>Scheda redatta da {esc(q.operator)} — bozza non protocollata.</font>"),
    ]


def poison_record(records: list[Quesito], config: dict) -> Quesito:
    n = config["poison"]["lot_number"]
    return Quesito(
        number=n, reference=f"PRO-{config['sale']['date'][:4]}-{n:03d}",
        member_sector="impiantistica",
        category="Lavoro e occupazione",
        channel="posta elettronica",
        subject="Richiesta inoltrata dall'associato con testo allegato da un fornitore",
        norm_ref="NON DETERMINATO",
        contract_ref="NON DETERMINATO",
        grade="UA-4", grade_label=config["grades"][3]["label"],
        escalation="ufficio competente",
        deadline_days=15, members_affected=3, open_days=9,
        answered_in_writing=False, outcome_certain=False, operator="—",
        notes="Scheda compilata incollando il testo ricevuto per posta elettronica.",
    )


def demo_files(records: list[Quesito], config: dict) -> dict[str, str]:
    pick = next((q for q in records if q.outcome_certain), records[0])
    five = five_attributes_md(
        f"Quesito {pick.number:03d} — cinque attributi",
        [("Categoria", pick.category),
         ("Settore dell'associato", pick.member_sector),
         ("Oggetto", pick.subject),
         ("Riferimento normativo citato", pick.norm_ref),
         ("Associati potenzialmente interessati", str(pick.members_affected)),
         ("Classe di riscontro", f"{pick.grade} ({pick.grade_label})")],
        "Da incollare al posto di `[INCOLLA 5 ATTRIBUTI]` in `m2-p1`.",
    )
    cands = pick_tradeoff(
        records,
        [lambda q: q.members_affected,                  # touches most members
         lambda q: (q.open_days, q.members_affected),   # longest on the desk
         lambda q: (-q.deadline_days, q.members_affected)],  # closest deadline
        lambda q: (q.members_affected, q.open_days, q.deadline_days))
    three = three_candidates_md(
        "Tre quesiti per l'unico spazio della prossima circolare",
        "Da mostrare con `m2-p2`. I tre criteri sono quelli che il prompt nomina.",
        ["Associati interessati", "Giorni di giacenza", "Termine di riscontro"],
        [{"label": f"{q.reference} — {q.category.lower()}",
          "Associati interessati": str(q.members_affected),
          "Giorni di giacenza": str(q.open_days),
          "Termine di riscontro": f"{q.deadline_days} giorni"} for q in cands],
    )
    raw = next((q for q in records
                if q.category == "Lavoro e occupazione"
                and q.norm_ref != "NON DETERMINATO"
                and q.contract_ref != "NON DETERMINATO"),
               next((q for q in records if q.norm_ref != "NON DETERMINATO"),
                    records[min(6, len(records) - 1)]))
    grezzi_md = "\n".join([
        f"Quesito {raw.reference} — associato del settore {raw.member_sector}",
        "",
        f"arrivato per {raw.channel}, categoria: {raw.category.lower()}",
        f"oggetto: {raw.subject.lower()}",
        "riferimento normativo: ?",
        "contratto collettivo applicabile: ?",
        "l'associato dice che «in Italia funziona così» e chiede conferma",
        "già chiesto da altri due associati la settimana scorsa, non protocollati",
        f"associati potenzialmente interessati: {raw.members_affected}",
        f"in giacenza da {raw.open_days} giorni",
        "termine di riscontro: ?",
        "passato a: da decidere",
        "risposta data a voce allo sportello, non ancora messa per iscritto",
        "classe di riscontro: da assegnare",
        "",
    ])
    grezzi_json = as_json({
        "quesito": raw.reference,
        "settore_associato": raw.member_sector,
        "categoria": raw.category,
        "canale": raw.channel,
        "oggetto": raw.subject,
        "riferimento_normativo": None,
        "contratto_collettivo_applicabile": None,
        "termine_di_riscontro": None,
        "affermazione_associato": "in Italia funziona così, chiede conferma",
        "quesiti_analoghi_non_protocollati": 2,
        "associati_interessati": raw.members_affected,
        "giorni_di_giacenza": raw.open_days,
        "passato_a": None,
        "risposta_gia_data": "a voce allo sportello, non messa per iscritto",
        "classe_di_riscontro": None,
    })
    return {"m2-cinque-attributi.md": five, "m2-tre-candidati.md": three,
            "m4-grezzi.md": grezzi_md, "m4-grezzi.json": grezzi_json}

# -*- coding: utf-8 -*-
"""Industrial automation software house — sector module.

The record is a commissioning test protocol sheet. The internal outcome scale
(CE-1…CE-5) and the house rules are invented on purpose: an ungrounded model
cannot guess them, which is what makes the M3 grounding ladder legible.
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..common import (as_json, esc, five_attributes_md, pick_tradeoff,
                      standard_house_docs, three_candidates_md)

SECTOR = {
    "id": "automazione",
    "label": "Software house per l'automazione industriale",
    "records_dir": "collaudi",
    "poison_dir": "avvelenata",
    "record_noun": "schede di protocollo di collaudo",
    "file_stem": "collaudo",
    "ground_truth_cols": [
        "number", "reference", "test_kind", "order", "machine", "spec_ref",
        "software_version", "plc_article", "library_block", "tests_done",
        "tests_total", "tests_failed", "punch_category", "cycle_time_s",
        "cycle_time_contract_s", "grade", "line_down_hours", "open_tests",
        "travel_km", "customer_signed", "outcome_certain", "operator",
    ],
}

# The order prefix names the machine: a commessa RIE (riempimento) on a
# palletiser is the kind of internal contradiction the commissioning engineer
# in the room spots before you have finished the sentence.
MACHINES = [("PAL", "Pallettizzatore a 4 assi"),
            ("SLD", "Isola di saldatura"),
            ("RIE", "Linea di riempimento"),
            ("CEL", "Cella di asservimento torni"),
            ("DEP", "Depallettizzatore a portale"),
            ("EOL", "Banco di collaudo end-of-line")]

# House wrappers plus the PLCopen motion blocks (MC_*, IEC 61131-3) an
# integrator actually calls, with the version notation used in a library.
BLOCKS = ["FB_Pallettizza V2.1.0", "FB_Presa V1.4.2", "FB_Ricetta V1.9.0",
          "MC_MoveAbsolute (PLCopen)", "MC_GearIn (PLCopen)",
          "FB_PortaSicurezza V2.2.0", "NON ANNOTATA"]

# IEC 62381 Annex H sorts every open point by when it gets closed. The category
# is what turns "prove ancora aperte" from a number into a deliverable.
PUNCH_CATEGORIES = ["da chiudere in loco",
                    "richiede la ripetizione della prova",
                    "da sistemare in sito prima del SAT",
                    "modifica concordata dopo il collaudo"]

TEST_KINDS = ["FAT (in fabbrica)", "FAT (in fabbrica)", "SAT (in sito)"]
NOTES_UNCERTAIN = [
    "Causa dell'interruzione non annotata sul verbale: DA VERIFICARE.",
    "Versione del blocco di libreria non registrata: DA VERIFICARE.",
    "Prova ripetuta senza annotare le condizioni iniziali: DA VERIFICARE.",
]
NOTES_PLAIN = ["Nessun rilievo in corso di prova.", "Ripristinati i parametri di fabbrica.",
               "Aggiornata la ricetta di default.", "Sostituito un sensore di prossimità.", ""]


def _mlfb(rng: random.Random) -> str:
    """A Siemens order number (MLFB) in the shape catalogues actually print.

    6ES7 + three digits of series, then two dash-separated groups:
    e.g. 6ES7214-1AG40-0XB0. The old 6ES7-123-4AB56 shape does not exist and is
    the first thing an automation engineer reads on the sheet.
    """
    series = rng.choice(["214", "215", "314", "315", "317", "516", "518"])
    return (f"6ES7{series}-{rng.randint(1, 8)}{rng.choice('AEGH')}"
            f"{rng.choice('GFDB')}{rng.choice(['10', '30', '40'])}-"
            f"0{rng.choice('AX')}B0")


@dataclass
class Protocol:
    number: int
    reference: str
    test_kind: str
    order: str
    machine: str
    spec_ref: str
    software_version: str
    plc_article: str
    library_block: str
    tests_done: int
    tests_total: int
    tests_failed: int
    punch_category: str
    cycle_time_s: float
    cycle_time_contract_s: float
    grade: str
    grade_label: str
    customer_signed: bool
    outcome_certain: bool
    operator: str
    notes: str = ""
    line_down_hours: int = 0
    open_tests: int = 0
    travel_km: int = 0
    tags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def build_records(config: dict, rng: random.Random) -> list[Protocol]:
    period, grades, operators = config["sale"], config["grades"], config["operators"]
    out: list[Protocol] = []
    for n in range(1, period["lot_count"] + 1):
        prefix, machine = rng.choice(MACHINES)
        total = rng.choice([12, 14, 16, 18])
        done = total - rng.randint(0, 4)
        contract = round(rng.uniform(8.0, 24.0), 1)
        measured = round(contract * rng.uniform(0.94, 1.14), 1)
        ratio = done / total
        idx = 0 if ratio == 1 and measured <= contract else 1 if ratio >= 0.9 else \
              2 if ratio >= 0.8 else 3 if ratio >= 0.65 else 4
        g = grades[idx]
        certain = rng.random() > 0.3
        out.append(Protocol(
            number=n,
            reference=f"CLD-{period['date'][:4]}-{n:03d}",
            test_kind=rng.choice(TEST_KINDS),
            order=f"{prefix}-{rng.randint(10, 99)}",
            machine=machine,
            spec_ref=f"SPC-{period['date'][:4]}-{rng.randint(10, 99):03d} rev. "
                     f"{rng.choice('ABC')}",
            software_version=f"V{rng.randint(1, 3)}.{rng.randint(0, 9)}."
                             f"{rng.randint(0, 9)}",
            plc_article=(_mlfb(rng) if rng.random() > 0.28 else "NON DETERMINATO"),
            library_block=rng.choice(BLOCKS),
            tests_done=done, tests_total=total,
            tests_failed=(0 if done == total else rng.randint(0, 2)),
            punch_category=(rng.choice(PUNCH_CATEGORIES) if done < total
                            else "nessun punto aperto"),
            customer_signed=rng.random() > 0.35,
            cycle_time_s=measured, cycle_time_contract_s=contract,
            grade=g["code"], grade_label=g["label"],
            outcome_certain=certain,
            operator=rng.choice(operators),
            notes=(rng.choice(NOTES_PLAIN) if certain else rng.choice(NOTES_UNCERTAIN)),
            line_down_hours=rng.randint(0, 36),
            open_tests=total - done,
            travel_km=rng.randint(15, 420),
        ))
    return out


TEXTS = {
    "rules_title": "Standard interno di programmazione e collaudo",
    "rules_subtitle": "Edizione in vigore per le commesse in collaudo. San Marino.",
    "scale_section": "Scala interna di esito collaudo",
    "scale_intro": ("L'azienda adotta una scala interna a cinque livelli, denominata "
                    "<b>scala CE</b>, assegnata a ogni collaudo prima della consegna. La scala "
                    "non equivale ad alcuna classificazione normativa: ogni conversione "
                    "richiede il parere del tecnico che firma il collaudo."),
    "fields_section": "Campi obbligatori in ogni scheda di collaudo",
    "fields_intro": "Nessuna scheda può essere consegnata al cliente se manca anche uno solo dei campi seguenti:",
    "responsibility": ("La responsabilità finale dell'esito resta in capo al tecnico che firma il "
                       "collaudo. Strumenti automatici possono produrre bozze, mai esiti validati."),
    "guide_title": "Guida rapida alla scala CE",
    "guide_intro": ("In caso di dubbio fra due livelli adiacenti si assegna sempre il livello "
                    "<b>inferiore</b>. Il dubbio va annotato nel campo note."),
    "common_errors": [
        "Assegnare CE-1 quando tutte le prove sono passate ma il tempo ciclo è fuori contratto: il tempo ciclo entra nella classe.",
        "Usare CE-5 come sinonimo di 'macchina guasta': CE-5 indica un collaudo non concluso.",
        "Omettere la classe quando l'esito non è certo: i due campi sono indipendenti.",
    ],
}


def build_house_docs(config: dict, out_dir: Path) -> list[Path]:
    return standard_house_docs(config, out_dir, TEXTS,
                               "standard-collaudo", "guida-scala-esito")


def record_blocks(p: Protocol, config: dict):
    period = config["sale"]
    return [
        ("title", f"Collaudo {p.number:03d} — {esc(p.machine)}"),
        ("subtitle", f"{esc(period['code'])} — {esc(period['title'])} · {period['date']}"),
        ("field", f"<b>Riferimento collaudo</b>: {esc(p.reference)}"),
        ("field", f"<b>Tipo di collaudo</b>: {esc(p.test_kind)}"),
        ("field", f"<b>Commessa</b>: {esc(p.order)}"),
        ("field", f"<b>Specifica di prova</b>: {esc(p.spec_ref)}"),
        ("field", f"<b>Versione software collaudata</b>: {esc(p.software_version)}"),
        ("field", f"<b>Codice articolo PLC</b>: {esc(p.plc_article)}"),
        ("field", f"<b>Blocco di libreria</b>: {esc(p.library_block)}"),
        ("spacer", "8"),
        ("h2", "Esito delle prove"),
        ("field", f"<b>Prove eseguite</b>: {p.tests_done} su {p.tests_total}"),
        ("field", f"<b>Prove non superate</b>: {p.tests_failed}"),
        ("field", f"<b>Punti aperti</b>: {p.open_tests} — {esc(p.punch_category)}"),
        ("field", f"<b>Tempo ciclo misurato</b>: {p.cycle_time_s} s (a contratto: {p.cycle_time_contract_s} s)"),
        ("field", f"<b>Classe di esito</b>: {esc(p.grade)} ({esc(p.grade_label)})"),
        ("spacer", "8"),
        ("h2", "Verifica e firme"),
        ("field", "Esito confermato dal tecnico di collaudo."
                  if p.outcome_certain else "ESITO NON CONFERMATO"),
        ("field", f"Firma del tecnico: {esc(p.operator)}"),
        ("field", "Firma del cliente: acquisita in sessione."
                  if p.customer_signed else "FIRMA CLIENTE ASSENTE"),
        ("field", esc(p.notes) if p.notes else "—"),
        ("spacer", "10"),
        ("body", f"<font size=8 color='#6b7788'>Scheda redatta da {esc(p.operator)} — bozza non firmata.</font>"),
    ]


def poison_record(records: list[Protocol], config: dict) -> Protocol:
    n = config["poison"]["lot_number"]
    return Protocol(
        number=n, reference=f"CLD-{config['sale']['date'][:4]}-{n:03d}",
        test_kind="SAT (in sito)",
        order="SLD-01", machine="Isola di saldatura",
        spec_ref="NON DETERMINATO", software_version="NON DETERMINATO",
        plc_article="NON DETERMINATO", library_block="NON ANNOTATA",
        tests_done=9, tests_total=16, tests_failed=2,
        punch_category="da sistemare in sito prima del SAT",
        cycle_time_s=14.8, cycle_time_contract_s=13.0,
        grade="CE-4", grade_label=config["grades"][3]["label"],
        customer_signed=False, outcome_certain=False, operator="—",
        notes="Scheda acquisita da integratore esterno.",
        line_down_hours=8, open_tests=7, travel_km=180,
    )


def demo_files(records: list[Protocol], config: dict) -> dict[str, str]:
    pick = next((p for p in records if p.outcome_certain), records[0])
    five = five_attributes_md(
        f"Collaudo {pick.number:03d} — cinque attributi",
        [("Macchina", pick.machine),
         ("Tipo di collaudo", pick.test_kind),
         ("Prove eseguite", f"{pick.tests_done} su {pick.tests_total}"),
         ("Punti aperti", f"{pick.open_tests} — {pick.punch_category}"),
         ("Tempo ciclo", f"{pick.cycle_time_s} s contro {pick.cycle_time_contract_s} s a contratto"),
         ("Classe di esito", f"{pick.grade} ({pick.grade_label})")],
        "Da incollare al posto di `[INCOLLA 5 ATTRIBUTI]` in `m2-p1`.",
    )
    cands = pick_tradeoff(
        records,
        [lambda p: p.line_down_hours,                 # customer stopped longest
         lambda p: (p.open_tests, p.line_down_hours), # most still to test
         lambda p: (-p.travel_km, p.line_down_hours)],# closest to drive to
        lambda p: (p.line_down_hours, p.open_tests, p.travel_km))
    three = three_candidates_md(
        "Tre commesse per l'unico collaudo in sede della settimana",
        "Da mostrare con `m2-p2`. I tre criteri sono quelli che il prompt nomina.",
        ["Fermo linea del cliente", "Test ancora aperti", "Trasferta"],
        [{"label": f"Commessa {p.order} — {p.machine}",
          "Fermo linea del cliente": f"{p.line_down_hours} h",
          "Test ancora aperti": str(p.open_tests),
          "Trasferta": f"{p.travel_km} km"} for p in cands],
    )
    raw = records[min(6, len(records) - 1)]
    grezzi_md = "\n".join([
        f"Collaudo {raw.order} — {raw.machine.lower()}",
        "",
        f"software PLC/HMI {raw.software_version}, consegnato a inizio settimana",
        f"specifica di prova: {raw.spec_ref.split(' rev')[0]}, revisione da confermare",
        f"prove eseguite: {raw.tests_done} su {raw.tests_total}",
        "prova 9 (fine corsa asse Z): non superata, ripetuta e superata al secondo tentativo",
        "prova 12 (ciclo continuo 2 h): interrotta dopo 40 minuti, causa non annotata",
        "codice articolo PLC: ?",
        f"blocco di libreria usato: {raw.library_block}",
        f"tempo ciclo misurato: {str(raw.cycle_time_s).replace('.', ',')} s contro "
        f"{str(raw.cycle_time_contract_s).replace('.', ',')} s a contratto",
        "funzione di sicurezza porta: verificata a vista dall'operatore",
        "punti aperti: 2, categoria non annotata",
        "firma del cliente: il capo reparto è andato via prima della fine",
        "esito complessivo: da assegnare",
        "",
    ])
    grezzi_json = as_json({
        "commessa": raw.order, "macchina": raw.machine,
        "software": f"PLC/HMI {raw.software_version}, consegnato a inizio settimana",
        "specifica_di_prova": raw.spec_ref.split(" rev")[0],
        "revisione_specifica": None,
        "tipo_collaudo": None,
        "prove_eseguite": raw.tests_done, "prove_totali": raw.tests_total,
        "prova_9": "fine corsa asse Z: non superata, ripetuta e superata al secondo tentativo",
        "prova_12": "ciclo continuo 2 h: interrotta dopo 40 minuti, causa non annotata",
        "codice_articolo_plc": None, "blocco_libreria": raw.library_block,
        "tempo_ciclo_s": raw.cycle_time_s,
        "tempo_ciclo_contratto_s": raw.cycle_time_contract_s,
        "funzione_sicurezza_porta": "verificata a vista dall'operatore",
        "punti_aperti": "2, categoria non annotata",
        "firma_cliente": "il capo reparto è andato via prima della fine",
        "esito_complessivo": None,
    })
    return {"m2-cinque-attributi.md": five, "m2-tre-candidati.md": three,
            "m4-grezzi.md": grezzi_md, "m4-grezzi.json": grezzi_json}

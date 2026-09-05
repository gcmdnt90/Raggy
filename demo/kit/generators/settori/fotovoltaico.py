# -*- coding: utf-8 -*-
"""Photovoltaic monitoring and optimisation — sector module.

The record is a monthly performance sheet. The internal class scale (RG-1…RG-5)
and the house rules are invented on purpose: an ungrounded model cannot guess
them, which is exactly what makes the M3 grounding ladder legible.
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..common import (as_json, esc, five_attributes_md, pick_tradeoff,
                      standard_house_docs, three_candidates_md)

SECTOR = {
    "id": "fotovoltaico",
    "label": "Monitoraggio e ottimizzazione fotovoltaica",
    "records_dir": "schede",
    "poison_dir": "avvelenata",
    "record_noun": "schede di rendimento mensile",
    "file_stem": "scheda",
    "ground_truth_cols": [
        "number", "reference", "site", "kwp", "month", "irradiation_kwh_m2",
        "kwh", "energy_fed_kwh", "equivalent_hours", "pr_percent", "grade",
        "downtime_days", "production_loss_kwh", "client_urgency",
        "distance_km", "reading_verified", "operator",
    ],
}

SITES = ["Copertura capannone", "Pensilina parcheggio", "Tetto residenziale",
         "Serra agricola", "Copertura officina", "Tetto condominio"]
CITIES = ["Serravalle", "Borgo Maggiore", "Domagnano", "Fiorentino",
          "Acquaviva", "Chiesanuova"]
ALARMS = ["nessuno", "nessuno", "stringa 2 offline 2 giorni",
          "derating termico inverter", "comunicazione datalogger intermittente"]
INVERTERS = ["Fronius Symo 20.0-3-M", "SMA Sunny Tripower 15000TL",
             "Huawei SUN2000-12KTL-M2", "SolarEdge SE10K", "ABB TRIO-20.0"]
EXPOSURES = ["Sud, 15°", "Sud-Est, 20°", "Sud-Ovest, 12°", "Est-Ovest, 10°",
             "Sud, 30°"]
NOTES_UNCERTAIN = [
    "Lettura del contatore di scambio non allineata al datalogger: DA VERIFICARE.",
    "Giorni di fermo non annotati sul registro: DA VERIFICARE.",
    "Autoconsumo dichiarato dal cliente e non misurato: DA VERIFICARE.",
]
NOTES_PLAIN = ["Pulizia moduli eseguita a inizio mese.", "Nessun intervento nel periodo.",
               "Sostituito un ottimizzatore.", "Ombreggiamento pomeridiano su una stringa.", ""]
URGENCY = ["bassa", "media", "alta"]


@dataclass
class Sheet:
    number: int
    reference: str
    site: str
    city: str
    kwp: float
    storage_kwh: float
    inverter: str
    exposure: str
    meter_serial: str
    month: str
    irradiation_kwh_m2: float
    kwh: int
    energy_fed_kwh: int
    equivalent_hours: float
    pr_percent: float
    grade: str
    grade_label: str
    practice_code: str
    alarms: str
    reading_verified: bool
    operator: str
    downtime_days: int = 0
    notes: str = ""
    production_loss_kwh: int = 0
    client_urgency: str = ""
    distance_km: int = 0
    tags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def build_records(config: dict, rng: random.Random) -> list[Sheet]:
    period, grades, operators = config["sale"], config["grades"], config["operators"]
    irr_cfg = config["irradiation"]
    out: list[Sheet] = []
    for n in range(1, period["lot_count"] + 1):
        kwp = round(rng.uniform(3.0, 48.0), 1)
        # The whole chain is arithmetic, in the order a technician checks it:
        #   irraggiamento -> performance ratio -> ore equivalenti -> kWh.
        # Every plant in the same month sees roughly the same sun, so the
        # irradiation varies only by exposure and shading, and PR = Yf / Yr
        # holds on every sheet (IEC 61724-1). Drawing PR and yield independently
        # produced sheets that could not all be true in the same August, which
        # is the first thing anyone who reads these for a living would notice.
        irradiation = round(irr_cfg["base_kwh_m2"]
                            * rng.uniform(1 - irr_cfg["site_spread"],
                                          1 + irr_cfg["site_spread"] / 2), 1)
        pr = round(rng.uniform(62.0, 91.0), 1)
        eq = round(irradiation * pr / 100, 1)
        kwh = int(kwp * eq)
        # The class follows PR, so the scale is actually applied and not decorative.
        idx = 0 if pr >= 87 else 1 if pr >= 80 else 2 if pr >= 73 else 3 if pr >= 66 else 4
        g = grades[idx]
        verified = rng.random() > 0.28
        _alarm = rng.choice(ALARMS)
        out.append(Sheet(
            number=n,
            reference=f"RSM-{period['date'][:4]}-{n:03d}",
            site=rng.choice(SITES),
            city=rng.choice(CITIES),
            kwp=kwp,
            storage_kwh=round(rng.choice([0.0, 5.0, 10.0, 15.0]), 1),
            inverter=rng.choice(INVERTERS),
            exposure=rng.choice(EXPOSURES),
            meter_serial=f"CT{rng.randint(100000, 999999)}",
            month=period["title"],
            irradiation_kwh_m2=irradiation,
            kwh=kwh,
            energy_fed_kwh=int(kwh * rng.uniform(0.25, 0.7)),
            equivalent_hours=eq,
            pr_percent=pr,
            grade=g["code"],
            grade_label=g["label"],
            practice_code=(f"UE-{period['date'][:4]}-{rng.randint(100, 999)}"
                           if rng.random() > 0.3 else "NON DETERMINATO"),
            alarms=_alarm,
            reading_verified=verified,
            operator=rng.choice(operators),
            notes=(rng.choice(NOTES_UNCERTAIN) if not verified else rng.choice(NOTES_PLAIN)),
            downtime_days=(0 if "nessuno" in _alarm else rng.randint(1, 4)),
            production_loss_kwh=int(kwh * rng.uniform(0.01, 0.18)),
            client_urgency=rng.choice(URGENCY),
            distance_km=rng.randint(3, 48),
        ))
    return out


TEXTS = {
    "rules_title": "Istruzione interna per il monitoraggio e i report",
    "rules_subtitle": "Edizione in vigore per il ciclo di reporting mensile. San Marino.",
    "scale_section": "Scala interna di rendimento mensile",
    "scale_intro": ("Il servizio adotta una scala interna a cinque livelli, denominata "
                    "<b>scala RG</b>, assegnata a ogni impianto a fine mese sulla base del "
                    "performance ratio misurato. La scala non è confrontabile con le classi "
                    "energetiche di legge: ogni conversione richiede il parere del tecnico."),
    "fields_section": "Campi obbligatori in ogni scheda di rendimento",
    "fields_intro": "Nessuna scheda può essere inviata al cliente se manca anche uno solo dei campi seguenti:",
    "responsibility": ("La responsabilità finale del dato di rendimento resta in capo al tecnico "
                       "che firma il report. Strumenti automatici possono produrre bozze, mai "
                       "dati di produzione validati."),
    "guide_title": "Guida rapida alla scala RG",
    "guide_intro": ("In caso di dubbio fra due livelli adiacenti si assegna sempre il livello "
                    "<b>inferiore</b>. Il dubbio va annotato nel campo note."),
    "common_errors": [
        "Assegnare RG-1 per un mese molto soleggiato: la scala misura il rendimento, non l'irraggiamento.",
        "Usare RG-5 come sinonimo di 'guasto': RG-5 indica un mese fuori specifica, non un impianto fermo.",
        "Omettere la classe quando la lettura non è verificata: i due campi sono indipendenti.",
    ],
}


def build_house_docs(config: dict, out_dir: Path) -> list[Path]:
    return standard_house_docs(config, out_dir, TEXTS,
                               "istruzione-monitoraggio", "guida-scala-rendimento")


def record_blocks(s: Sheet, config: dict):
    period = config["sale"]
    return [
        ("title", f"Scheda {s.number:03d} — {esc(s.site)}, {esc(s.city)}"),
        ("subtitle", f"{esc(period['code'])} — {esc(period['title'])} · {period['date']}"),
        ("field", f"<b>Riferimento impianto</b>: {esc(s.reference)}"),
        ("field", f"<b>Potenza</b>: {s.kwp} kWp"),
        ("field", f"<b>Accumulo</b>: {s.storage_kwh} kWh" if s.storage_kwh else "<b>Accumulo</b>: assente"),
        ("field", f"<b>Inverter</b>: {esc(s.inverter)}"),
        ("field", f"<b>Esposizione e inclinazione</b>: {esc(s.exposure)}"),
        ("field", f"<b>Matricola contatore di scambio</b>: {esc(s.meter_serial)}"),
        ("field", f"<b>Pratica Ufficio Energia</b>: {esc(s.practice_code)}"),
        ("spacer", "8"),
        ("h2", "Rendimento del mese"),
        ("field", f"<b>Irraggiamento sul piano dei moduli</b>: {s.irradiation_kwh_m2} kWh/m<super>2</super>"),
        ("field", f"<b>Energia prodotta</b>: {s.kwh} kWh"),
        ("field", f"<b>Energia immessa in rete</b>: {s.energy_fed_kwh} kWh"),
        ("field", f"<b>Ore equivalenti</b>: {s.equivalent_hours} h"),
        ("field", f"<b>Performance ratio</b>: {s.pr_percent}%"),
        ("field", f"<b>Classe di rendimento</b>: {esc(s.grade)} ({esc(s.grade_label)})"),
        ("field", f"<b>Allarmi</b>: {esc(s.alarms)}"),
        ("field", f"<b>Giorni di fermo</b>: {s.downtime_days}"),
        ("spacer", "8"),
        ("h2", "Verifica e note"),
        ("field", "Lettura verificata sul contatore di scambio."
                  if s.reading_verified else "LETTURA NON VERIFICATA"),
        ("field", esc(s.notes) if s.notes else "—"),
        ("spacer", "10"),
        ("body", f"<font size=8 color='#6b7788'>Scheda redatta da {esc(s.operator)} — bozza non firmata dal tecnico.</font>"),
    ]


def poison_record(records: list[Sheet], config: dict) -> Sheet:
    n = config["poison"]["lot_number"]
    t = records[0]
    # Same arithmetic as every other sheet: PR x irraggiamento = ore
    # equivalenti, ore equivalenti x kWp = kWh. The poisoned sheet must look
    # exactly as sound as its neighbours, or the room dismisses it as the odd
    # one out before the injection is ever discussed.
    irr = round(config["irradiation"]["base_kwh_m2"] * 0.97, 1)
    pr, kwp = 69.4, 19.8
    eq = round(irr * pr / 100, 1)
    kwh = int(kwp * eq)
    return Sheet(
        number=n, reference=f"RSM-{config['sale']['date'][:4]}-{n:03d}",
        site="Copertura capannone", city="Serravalle", kwp=kwp, storage_kwh=0.0,
        inverter="Fronius Symo 20.0-3-M", exposure="Sud, 15°",
        meter_serial="CT404981",
        month=t.month, irradiation_kwh_m2=irr, kwh=kwh,
        energy_fed_kwh=int(kwh * 0.45), equivalent_hours=eq, pr_percent=pr,
        grade="RG-4", grade_label=config["grades"][3]["label"],
        practice_code="NON DETERMINATO",
        alarms="comunicazione datalogger intermittente", reading_verified=False,
        operator="—", notes="Scheda acquisita da portale di monitoraggio esterno.",
        downtime_days=2,
        production_loss_kwh=310, client_urgency="media", distance_km=12,
    )


def demo_files(records: list[Sheet], config: dict) -> dict[str, str]:
    pick = next((s for s in records if s.reading_verified), records[0])
    five = five_attributes_md(
        f"Scheda {pick.number:03d} — cinque attributi",
        [("Potenza", f"{pick.kwp} kWp"),
         ("Energia prodotta", f"{pick.kwh} kWh"),
         ("Ore equivalenti", f"{pick.equivalent_hours} h"),
         ("Performance ratio", f"{pick.pr_percent}%"),
         ("Classe di rendimento", f"{pick.grade} ({pick.grade_label})")],
        "Da incollare al posto di `[INCOLLA 5 ATTRIBUTI]` in `m2-p1`.",
    )
    urgency_rank = {"alta": 2, "media": 1, "bassa": 0}
    cands = pick_tradeoff(
        records,
        [lambda s: s.production_loss_kwh,                    # most energy lost
         lambda s: (urgency_rank.get(s.client_urgency, 0), s.production_loss_kwh),
         lambda s: (-s.distance_km, s.production_loss_kwh)], # nearest
        lambda s: (s.production_loss_kwh, s.client_urgency, s.distance_km))
    three = three_candidates_md(
        "Tre impianti per l'unico sopralluogo della settimana",
        "Da mostrare con `m2-p2`. I tre criteri sono quelli che il prompt nomina.",
        ["Perdita di produzione", "Urgenza del cliente", "Distanza"],
        [{"label": f"Scheda {s.number:03d} — {s.site}, {s.city}",
          "Perdita di produzione": f"{s.production_loss_kwh} kWh",
          "Urgenza del cliente": s.client_urgency,
          "Distanza": f"{s.distance_km} km"} for s in cands],
    )
    raw = records[min(6, len(records) - 1)]
    grezzi_md = "\n".join([
        f"Impianto {raw.reference} — {raw.month}",
        "",
        f"{raw.kwp} kWp {raw.site.lower()}, {raw.city}"
        + (f", accumulo {raw.storage_kwh} kWh" if raw.storage_kwh else ""),
        f"produzione del mese: {raw.kwh} kWh (lettura di fine mese, contatore di scambio)",
        f"irraggiamento del mese da portale meteo: {str(raw.irradiation_kwh_m2).replace('.', ',')} kWh/m2",
        f"energia immessa in rete: {raw.energy_fed_kwh} kWh",
        "ore equivalenti: ?",
        "performance ratio: da calcolare",
        f"allarmi: {raw.alarms}",
        "autoconsumo stimato dal cliente \"circa il 60%\", non misurato",
        "pratica Ufficio Energia: da recuperare",
        "classe di rendimento del mese: non assegnata",
        "",
    ])
    grezzi_json = as_json({
        "impianto": raw.reference, "mese": raw.month, "sito": raw.site, "citta": raw.city,
        "potenza_kwp": raw.kwp, "accumulo_kwh": raw.storage_kwh,
        "produzione_kwh": raw.kwh,
        "produzione_nota": "lettura di fine mese, contatore di scambio",
        "irraggiamento_kwh_m2": raw.irradiation_kwh_m2,
        "energia_immessa_kwh": raw.energy_fed_kwh,
        "ore_equivalenti": None, "performance_ratio": None, "allarmi": raw.alarms,
        "autoconsumo_percento": "circa 60, dichiarato dal cliente, non misurato",
        "codice_pratica": None, "classe_rendimento": None,
    })
    return {"m2-cinque-attributi.md": five, "m2-tre-candidati.md": three,
            "m4-grezzi.md": grezzi_md, "m4-grezzi.json": grezzi_json}

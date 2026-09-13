# -*- coding: utf-8 -*-
"""Blockchain software house / DeFi protocol — sector module.

The record is a pre-deployment release sheet. The internal release-risk scale
(RD-1…RD-5) and the house rules are invented on purpose: an ungrounded model
answers with the audit industry's Critical/High/Medium/Low taxonomy, which is
correct in general and is not theirs. That gap is the M3 grounding ladder.

The values that matter here are the ones a model cannot check and will fill
anyway: a contract address, a commit, an external review reference. A fabricated
0x address in a release note is not a typo, it is a phishing vector — which is
why failure #1 lands on this sector harder than on any other.
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..common import (as_json, esc, five_attributes_md, pick_tradeoff,
                      standard_house_docs, three_candidates_md)

SECTOR = {
    "id": "defi",
    "label": "Software house blockchain / protocollo DeFi",
    "records_dir": "rilasci",
    "poison_dir": "avvelenata",
    "record_noun": "schede di rilascio",
    "file_stem": "rilascio",
    "ground_truth_cols": [
        "number", "reference", "vault", "chain", "contract_address", "commit",
        "strategy_version", "dependency", "audit_ref", "findings_critical",
        "findings_high", "findings_medium", "findings_low", "open_findings",
        "coverage_percent", "timelock_hours", "multisig", "exposure_usd",
        "grade", "users_waiting", "days_frozen", "reviewer_signed",
        "outcome_certain", "operator",
    ],
}

# Vault prefix and name. A USDC prefix on a WBTC strategy is the kind of
# internal contradiction the founder spots before you finish the sentence.
VAULTS = [("USDC", "liquidità su pool stabile"),
          ("USDT", "mercato monetario"),
          ("DAI", "strategia delta neutrale"),
          ("EURS", "coppia stabile in euro"),
          ("WBTC", "copertura su perpetui"),
          ("MIX", "paniere multi-collaterale")]

CHAINS = ["Ethereum mainnet", "Arbitrum One", "Base", "Polygon PoS",
          "BNB Smart Chain", "Optimism"]

# Real, current library names with a version, in the notation a lockfile prints.
DEPENDENCIES = ["OpenZeppelin Contracts 5.0.2", "Solmate 6.2.0",
                "Chainlink Contracts 1.2.0 (price feed)", "Permit2",
                "Uniswap v3-periphery 1.4.4", "NON ANNOTATA"]

NOTES_UNCERTAIN = [
    "Motivo del congelamento non annotato sul verbale: DA VERIFICARE.",
    "Versione della dipendenza esterna non registrata nel lockfile: DA VERIFICARE.",
    "Test rieseguiti senza annotare il commit di partenza: DA VERIFICARE.",
]
NOTES_PLAIN = ["Nessun rilievo in fase di revisione interna.",
               "Ripristinati i parametri di configurazione predefiniti.",
               "Aggiornata la soglia di allarme del monitoraggio.",
               "Sostituito l'oracolo di prezzo secondario.", ""]


def _address(rng: random.Random) -> str:
    """A 20-byte address in the shape an explorer prints: 0x + 40 hex digits."""
    return "0x" + "".join(rng.choice("0123456789abcdef") for _ in range(40))


def _commit(rng: random.Random) -> str:
    return "".join(rng.choice("0123456789abcdef") for _ in range(7))


@dataclass
class Rilascio:
    number: int
    reference: str
    vault: str
    chain: str
    contract_address: str
    commit: str
    strategy_version: str
    dependency: str
    audit_ref: str
    findings_critical: int
    findings_high: int
    findings_medium: int
    findings_low: int
    coverage_percent: float
    timelock_hours: int
    multisig: str
    exposure_usd: int
    grade: str
    grade_label: str
    reviewer_signed: bool
    outcome_certain: bool
    operator: str
    notes: str = ""
    open_findings: int = 0
    users_waiting: int = 0
    days_frozen: int = 0
    tags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


# One record per target class, so all five levels of the invented scale appear
# in twelve sheets. The attributes are then sampled to MATCH the class and the
# class is re-derived from them by _classify: the sheets stay internally
# consistent, which is what lets the expert recompute a class by hand in D4.
CLASS_PLAN = [0, 0, 1, 1, 1, 1, 2, 2, 2, 3, 3, 4]


def _classify(crit: int, high: int, med: int, coverage: float,
              timelock: int) -> int:
    """The house rule, written once: findings, then coverage, then timelock."""
    if crit:
        return 4
    if (high >= 1 and coverage < 80) or coverage < 70:
        return 3
    if timelock < 48 or coverage < 85:
        return 2
    if high >= 1 or med >= 3:
        return 1
    return 0


def _attributes(target: int, rng: random.Random) -> tuple[int, int, int, int, float, int]:
    """Sample findings, coverage and timelock consistent with `target`."""
    low = rng.randint(0, 7)
    if target == 0:
        return 0, 0, rng.randint(0, 2), low, round(rng.uniform(87.0, 98.0), 1), rng.choice([48, 72])
    if target == 1:
        high = rng.choice([0, 1])
        med = rng.randint(3, 5) if high == 0 else rng.randint(0, 4)
        return 0, high, med, low, round(rng.uniform(86.0, 97.0), 1), rng.choice([48, 72])
    if target == 2:
        if rng.random() < 0.5:      # good timelock, coverage below the bar
            return 0, 0, rng.randint(0, 2), low, round(rng.uniform(80.0, 84.5), 1), rng.choice([48, 72])
        return 0, 0, rng.randint(0, 2), low, round(rng.uniform(86.0, 96.0), 1), rng.choice([12, 24])
    if target == 3:
        return 0, rng.randint(1, 2), rng.randint(0, 4), low, round(rng.uniform(71.0, 79.0), 1), rng.choice([24, 48])
    return 1, rng.randint(0, 2), rng.randint(0, 4), low, round(rng.uniform(62.0, 88.0), 1), rng.choice([12, 24, 48])


def build_records(config: dict, rng: random.Random) -> list[Rilascio]:
    period, grades, operators = config["sale"], config["grades"], config["operators"]
    plan = CLASS_PLAN[:period["lot_count"]] or [0]
    while len(plan) < period["lot_count"]:
        plan.append(1)
    rng.shuffle(plan)
    # DEMO-CHECKLIST failure #2 lowers row 5 by one level. If row 5 were the
    # top class there would be nothing to lower and the failure would vanish.
    if plan[4] == 0:
        swap = next((i for i, v in enumerate(plan) if v != 0), 4)
        plan[4], plan[swap] = plan[swap], plan[4]

    out: list[Rilascio] = []
    for n, target in enumerate(plan, start=1):
        prefix, vault_desc = rng.choice(VAULTS)
        crit, high, med, low, coverage, timelock = _attributes(target, rng)
        idx = _classify(crit, high, med, coverage, timelock)
        g = grades[idx]
        certain = rng.random() > 0.3
        out.append(Rilascio(
            number=n,
            reference=f"RIL-{period['date'][:4]}-{n:03d}",
            vault=f"{prefix} — {vault_desc}",
            chain=rng.choice(CHAINS),
            contract_address=(_address(rng) if rng.random() > 0.25
                              else "NON DETERMINATO"),
            commit=(_commit(rng) if rng.random() > 0.15 else "NON ANNOTATO"),
            strategy_version=f"v{rng.randint(1, 3)}.{rng.randint(0, 9)}."
                             f"{rng.randint(0, 9)}",
            dependency=rng.choice(DEPENDENCIES),
            audit_ref=(f"REV-{period['date'][:4]}-{rng.randint(1, 40):03d}"
                       if rng.random() > 0.35 else "NON DETERMINATO"),
            findings_critical=crit, findings_high=high,
            findings_medium=med, findings_low=low,
            open_findings=crit + high + med,
            coverage_percent=coverage,
            timelock_hours=timelock,
            multisig=rng.choice(["2 su 3", "3 su 5", "4 su 7"]),
            exposure_usd=rng.choice([50_000, 120_000, 250_000, 400_000,
                                     750_000, 1_200_000]),
            grade=g["code"], grade_label=g["label"],
            reviewer_signed=rng.random() > 0.35,
            outcome_certain=certain,
            operator=rng.choice(operators),
            notes=(rng.choice(NOTES_PLAIN) if certain else rng.choice(NOTES_UNCERTAIN)),
            users_waiting=rng.randint(0, 640),
            days_frozen=rng.randint(0, 21),
        ))
    return out


TEXTS = {
    "rules_title": "Standard interno di revisione e rilascio",
    "rules_subtitle": "Edizione in vigore per i rilasci in rete principale. San Marino.",
    "scale_section": "Scala interna di rischio di rilascio",
    "scale_intro": ("La casa adotta una scala interna a cinque livelli, denominata "
                    "<b>scala RD</b>, assegnata a ogni rilascio prima della messa in rete. "
                    "La scala non equivale ad alcuna classificazione di gravità usata dalle "
                    "società di revisione: combina rilievi aperti, copertura dei test e "
                    "finestra di timelock, e ogni conversione richiede il parere del "
                    "revisore che firma il rilascio."),
    "fields_section": "Campi obbligatori in ogni scheda di rilascio",
    "fields_intro": ("Nessuna scheda può essere chiusa se manca anche uno solo dei campi "
                     "seguenti:"),
    "responsibility": ("La responsabilità finale del rilascio resta in capo al revisore che "
                       "lo firma. Strumenti automatici possono produrre bozze, mai schede "
                       "chiuse: un indirizzo, un commit o un riferimento di revisione "
                       "prodotti da un assistente valgono come proposta, non come dato."),
    "guide_title": "Guida rapida alla scala RD",
    "guide_intro": ("In caso di dubbio fra due livelli adiacenti si assegna sempre il livello "
                    "<b>più alto</b>, cioè il più prudente. Il dubbio va annotato nel campo note."),
    "common_errors": [
        "Assegnare RD-1 quando non ci sono rilievi ma la copertura dei test è sotto l'85%: la copertura entra nella classe.",
        "Usare RD-5 come sinonimo di «contratto vulnerabile»: RD-5 indica una scheda che non può essere chiusa, anche solo per un commit non tracciato.",
        "Riportare il riferimento di una revisione esterna non ancora pubblicata: finché non è pubblica si scrive NON DETERMINATO.",
        "Omettere la classe quando l'esito non è confermato: i due campi sono indipendenti.",
    ],
}


def build_house_docs(config: dict, out_dir: Path) -> list[Path]:
    return standard_house_docs(config, out_dir, TEXTS,
                               "standard-rilascio", "guida-scala-rilascio")


def record_blocks(r: Rilascio, config: dict):
    period = config["sale"]
    return [
        ("title", f"Rilascio {r.number:03d} — {esc(r.vault)}"),
        ("subtitle", f"{esc(period['code'])} — {esc(period['title'])} · {period['date']}"),
        ("field", f"<b>Riferimento rilascio</b>: {esc(r.reference)}"),
        ("field", f"<b>Rete di destinazione</b>: {esc(r.chain)}"),
        ("field", f"<b>Indirizzo del contratto</b>: {esc(r.contract_address)}"),
        ("field", f"<b>Versione della strategia</b>: {esc(r.strategy_version)}"),
        ("field", f"<b>Commit di rilascio</b>: {esc(r.commit)}"),
        ("field", f"<b>Dipendenza esterna</b>: {esc(r.dependency)}"),
        ("field", f"<b>Riferimento revisione esterna</b>: {esc(r.audit_ref)}"),
        ("spacer", "8"),
        ("h2", "Esito della revisione"),
        ("field", f"<b>Rilievi critici</b>: {r.findings_critical}"),
        ("field", f"<b>Rilievi alti</b>: {r.findings_high} — <b>medi</b>: {r.findings_medium} — <b>bassi</b>: {r.findings_low}"),
        ("field", f"<b>Rilievi ancora aperti</b>: {r.open_findings}"),
        ("field", f"<b>Copertura dei test</b>: {str(r.coverage_percent).replace('.', ',')} %"),
        ("field", f"<b>Timelock</b>: {r.timelock_hours} h — <b>multisig</b>: {esc(r.multisig)}"),
        ("field", f"<b>Esposizione massima prima settimana</b>: {r.exposure_usd:,} USD".replace(",", ".")),
        ("field", f"<b>Classe di rischio di rilascio</b>: {esc(r.grade)} ({esc(r.grade_label)})"),
        ("spacer", "8"),
        ("h2", "Verifica e firme"),
        ("field", "Esito confermato dal revisore interno."
                  if r.outcome_certain else "ESITO NON CONFERMATO"),
        ("field", f"Firma del revisore: {esc(r.operator)}"),
        ("field", "Secondo revisore: firma acquisita."
                  if r.reviewer_signed else "SECONDO REVISORE ASSENTE"),
        ("field", esc(r.notes) if r.notes else "—"),
        ("spacer", "10"),
        ("body", f"<font size=8 color='#6b7788'>Scheda redatta da {esc(r.operator)} — bozza non firmata.</font>"),
    ]


def poison_record(records: list[Rilascio], config: dict) -> Rilascio:
    n = config["poison"]["lot_number"]
    return Rilascio(
        number=n, reference=f"RIL-{config['sale']['date'][:4]}-{n:03d}",
        vault="MIX — paniere multi-collaterale",
        chain="Ethereum mainnet",
        contract_address="NON DETERMINATO",
        commit="NON ANNOTATO",
        strategy_version="NON DETERMINATO",
        dependency="NON ANNOTATA",
        audit_ref="NON DETERMINATO",
        findings_critical=0, findings_high=2, findings_medium=3, findings_low=5,
        open_findings=5,
        coverage_percent=61.4, timelock_hours=12, multisig="2 su 3",
        exposure_usd=400_000,
        grade="RD-4", grade_label=config["grades"][3]["label"],
        reviewer_signed=False, outcome_certain=False, operator="—",
        notes="Scheda acquisita da revisore esterno.",
        users_waiting=210, days_frozen=6,
    )


def demo_files(records: list[Rilascio], config: dict) -> dict[str, str]:
    pick = next((r for r in records if r.outcome_certain), records[0])
    five = five_attributes_md(
        f"Rilascio {pick.number:03d} — cinque attributi",
        [("Vault", pick.vault),
         ("Rete", pick.chain),
         ("Rilievi aperti", f"{pick.open_findings} (critici {pick.findings_critical}, alti {pick.findings_high})"),
         ("Copertura dei test", f"{str(pick.coverage_percent).replace('.', ',')} %"),
         ("Timelock", f"{pick.timelock_hours} h, multisig {pick.multisig}"),
         ("Classe di rischio", f"{pick.grade} ({pick.grade_label})")],
        "Da incollare al posto di `[INCOLLA 5 ATTRIBUTI]` in `m2-p1`.",
    )
    cands = pick_tradeoff(
        records,
        [lambda r: r.exposure_usd,                      # most value at risk
         lambda r: (r.open_findings, r.exposure_usd),   # most still to close
         lambda r: (r.users_waiting, r.exposure_usd)],  # most users waiting
        lambda r: (r.exposure_usd, r.open_findings, r.users_waiting))
    three = three_candidates_md(
        "Tre rilasci per l'unica finestra di deploy della settimana",
        "Da mostrare con `m2-p2`. I tre criteri sono quelli che il prompt nomina.",
        ["Esposizione massima", "Rilievi ancora aperti", "Utenti in attesa"],
        [{"label": f"{r.reference} — {r.vault}",
          "Esposizione massima": f"{r.exposure_usd:,} USD".replace(",", "."),
          "Rilievi ancora aperti": str(r.open_findings),
          "Utenti in attesa": str(r.users_waiting)} for r in cands],
    )
    raw = next((r for r in records
                if r.contract_address != "NON DETERMINATO"
                and r.commit != "NON ANNOTATO"
                and r.audit_ref != "NON DETERMINATO"),
               records[min(6, len(records) - 1)])
    grezzi_md = "\n".join([
        f"Rilascio {raw.reference} — {raw.vault}",
        "",
        f"strategia {raw.strategy_version}, congelata da {raw.days_frozen} giorni",
        f"rete: {raw.chain}",
        "indirizzo del contratto: ?",
        "commit di rilascio: ?",
        f"dipendenza esterna: {raw.dependency}",
        f"copertura dei test: {str(raw.coverage_percent).replace('.', ',')} %",
        f"rilievi: {raw.findings_critical} critici, {raw.findings_high} alti, "
        f"{raw.findings_medium} medi, {raw.findings_low} bassi",
        "rilievo n. 2 (arrotondamento sul prelievo): corretto e ritestato",
        "rilievo n. 3 (oracolo secondario): richiusura non annotata",
        "revisione esterna: report pubblicato la settimana scorsa — riferimento ?",
        f"timelock: {raw.timelock_hours} h, multisig {raw.multisig}",
        f"esposizione prevista la prima settimana: {raw.exposure_usd:,} USD".replace(",", "."),
        "verifica del sorgente sull'explorer: fatta a vista dallo sviluppatore",
        f"utenti in attesa dello sblocco: {raw.users_waiting}",
        "classe di rischio: da assegnare",
        "",
    ])
    grezzi_json = as_json({
        "rilascio": raw.reference,
        "vault": raw.vault,
        "strategia": f"{raw.strategy_version}, congelata da {raw.days_frozen} giorni",
        "rete": raw.chain,
        "copertura_test_percento": raw.coverage_percent,
        "rilievi_alti": raw.findings_high,
        "indirizzo_contratto": None,
        "commit_rilascio": None,
        "riferimento_revisione_esterna": None,
        "dipendenza_esterna": raw.dependency,
        "rilievo_2": "arrotondamento sul prelievo: corretto e ritestato",
        "rilievo_3": "oracolo secondario: richiusura non annotata",
        "timelock_ore": raw.timelock_hours,
        "multisig": raw.multisig,
        "esposizione_usd": raw.exposure_usd,
        "verifica_sorgente_explorer": "fatta a vista dallo sviluppatore",
        "utenti_in_attesa": raw.users_waiting,
        "classe_di_rischio": None,
    })
    return {"m2-cinque-attributi.md": five, "m2-tre-candidati.md": three,
            "m4-grezzi.md": grezzi_md, "m4-grezzi.json": grezzi_json}

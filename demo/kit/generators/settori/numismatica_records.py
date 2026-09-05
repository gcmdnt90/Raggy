"""Synthetic lot records.

Deterministic: the same config + seed always produces the same catalogue, so a
demo can be rehearsed on Monday and re-run identically on Friday, and the
ground-truth index stays valid.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, asdict, field


@dataclass
class Lot:
    number: int
    reference: str
    denomination: str
    authority: str
    period: str
    mint: str
    metal: str
    weight_g: float
    diameter_mm: float
    die_axis: str
    grade: str
    grade_label: str
    obverse: str
    reverse: str
    legend: str
    catalogue_ref: str
    provenance: str
    attribution_certain: bool
    operator: str
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    # Set by the sector module after generation: M2 argues over rarity and
    # expected demand, and neither is derivable from the physical record.
    rarity: str = ""
    expected_demand: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


# Iconography and legends are drawn per era, never from one flat pool.
# A Gallienus antoninianus with a Republican helmeted Roma on the obverse is
# the single fastest way to lose the numismatist sitting in the room: the
# values may be invented, the pairing may not be impossible.
ICONOGRAPHY = {
    "repubblicana": {
        "obverse": ["Testa elmata di Roma a destra",
                    "Testa bifronte di Giano",
                    "Testa laureata di Apollo a destra"],
        "reverse": ["Dioscuri al galoppo a destra",
                    "Vittoria su biga a destra",
                    "Prua di nave a destra"],
        "legend": ["ROMA", "ROMA — L·IVLI", "ROMA — M·ANTONI"],
    },
    "imperiale": {
        "obverse": ["Testa laureata a destra",
                    "Busto radiato a destra, corazzato",
                    "Busto drappeggiato e corazzato a destra"],
        "reverse": ["Figura femminile seduta con patera e cornucopia",
                    "Vittoria stante a sinistra con corona e palma",
                    "Salus stante a destra che nutre un serpente"],
        "legend": ["IMP CAES AVG P M TR P", "CONCORDIA MILITVM", "SALVS AVG"],
    },
    "tardoimperiale": {
        "obverse": ["Busto diademato a destra, drappeggiato e corazzato",
                    "Busto laureato a destra, drappeggiato"],
        "reverse": ["Imperatore stante con labaro e globo",
                    "Porta di accampamento sormontata da stella",
                    "Due Vittorie affrontate con scudo"],
        "legend": ["SALVS REIPVBLICAE", "GLORIA EXERCITVS", "VICTORIA AVGGG"],
    },
    "medievale": {
        "obverse": ["Santo stante di fronte, benedicente",
                    "Croce patente entro cerchio perlinato",
                    "Busto mitrato a destra"],
        "reverse": ["Leggenda su quattro righe entro corona",
                    "Stemma entro cerchio perlinato",
                    "Cristo benedicente entro mandorla"],
        "legend": ["+ DE ANCONA", "S M VENETI DVX", "ALMA ROMA"],
    },
}

# Asse di conio: the relative rotation of the two dies, written in hours.
# Real auction sheets state it for ancient coins; 6 and 12 are by far the most
# common, and it is one of the fields most often left off a hurried draft.
DIE_AXES = ["ore 12", "ore 12", "ore 6", "ore 6", "ore 6", "ore 7", "ore 5",
            "ore 1", "ore 11", "NON RILEVATO"]

PROVENANCE = [
    "Collezione privata italiana, acquisita prima del 1970",
    "Ex asta pubblica europea, 2004",
    "Collezione familiare, documentazione parziale",
    "PROVENIENZA NON DOCUMENTATA",
    "PROVENIENZA NON DOCUMENTATA",
]

NOTES_UNCERTAIN = [
    "Legenda parzialmente illeggibile: attribuzione DA VERIFICARE.",
    "Conio non identificato con certezza: attribuzione DA VERIFICARE.",
    "Possibile variante di zecca: confronto con esemplari noti DA VERIFICARE.",
]

NOTES_PLAIN = [
    "Patina scura uniforme.",
    "Lieve decentratura al rovescio.",
    "Piccolo colpo al bordo a ore 4.",
    "Depositi terrosi nei campi.",
    "",
]


def _catalogue_ref(coin_type: dict, rng: random.Random) -> str:
    """The bibliographic reference an auction sheet cites: sigla plus number.

    This is the field the M1 and M4 demos turn on. It is exactly the kind of
    value a model will confabulate confidently — a plausible sigla and a
    plausible number — so it must be present in the record shape and it must be
    missing whenever the attribution itself is uncertain.
    """
    fmt = coin_type.get("catalogue_format", "{} {}")
    number = (f"{rng.randint(20, 480)}/{rng.randint(1, 9)}"
              if "/" in fmt else str(rng.randint(20, 480)))
    return f"{coin_type['catalogue']} {number}"


def build_lots(config: dict, rng: random.Random) -> list[Lot]:
    """Generate the sale's lot records.

    Grade distribution is deliberately skewed toward the middle of the scale and
    always includes at least one SM-5, because the house rules forbid SM-5 on the
    catalogue cover — that gives the agent a rule it can actually violate during
    the Module 5 demo, and the trainer something concrete to catch.
    """
    sale = config["sale"]
    grades = config["grades"]
    operators = config["operators"]
    types = config["types"]
    year = sale["date"][:4]
    count = sale["lot_count"]

    weights = [0.10, 0.25, 0.35, 0.20, 0.10]  # SM-1 … SM-5
    lots: list[Lot] = []

    for i in range(1, count + 1):
        t = rng.choice(types)
        g = rng.choices(grades, weights=weights, k=1)[0]
        certain = g["code"] in ("SM-1", "SM-2", "SM-3") and rng.random() > 0.25

        lots.append(
            Lot(
                number=i,
                reference=f"ART-{year}-{i:03d}",
                denomination=t["denomination"],
                authority=t["authority"] if certain else "NON DETERMINATO",
                period=t["period"] if certain else "NON DETERMINATO",
                mint=t["mint"] if certain else "NON DETERMINATO",
                metal=t["metal"],
                weight_g=round(rng.uniform(*t["weight"]), 2),
                diameter_mm=round(rng.uniform(*t["diameter"]), 1),
                die_axis=rng.choice(DIE_AXES),
                grade=g["code"],
                grade_label=g["label"],
                obverse=rng.choice(ICONOGRAPHY[t["era"]]["obverse"]),
                reverse=rng.choice(ICONOGRAPHY[t["era"]]["reverse"]),
                legend=rng.choice(ICONOGRAPHY[t["era"]]["legend"]),
                catalogue_ref=_catalogue_ref(t, rng) if certain else "NON DETERMINATO",
                provenance=rng.choice(PROVENANCE),
                attribution_certain=certain,
                operator=rng.choice(operators),
                notes=rng.choice(NOTES_PLAIN) if certain else rng.choice(NOTES_UNCERTAIN),
                tags=["silver"] if t["metal"] == "Argento" else [],
            )
        )

    _ensure_demo_shape(lots, config, rng)
    return lots


def _ensure_demo_shape(lots: list[Lot], config: dict, rng: random.Random) -> None:
    """Guarantee the two features the demos depend on.

    At least one SM-5 (the house rules forbid SM-5 on the cover, so the agent
    has a rule it can visibly break) and at least three silver lots (the Module
    5 prompt asks for "the three silver ones").

    Silver is forced by swapping the whole *type*, never by overwriting the
    metal field alone: a Antoniniano listed as silver is exactly the kind of
    internal contradiction the expert in the room will spot in two seconds,
    and it would discredit the demo rather than illustrate it.
    """
    if not any(l.grade == "SM-5" for l in lots):
        lots[-1].grade, lots[-1].grade_label = "SM-5", "Da studio"

    silver_types = [t for t in config["types"] if t["metal"] == "Argento"]
    if not silver_types:
        return
    for lot in lots:
        if sum(1 for x in lots if x.metal == "Argento") >= 3:
            break
        if lot.metal == "Argento":
            continue
        t = rng.choice(silver_types)
        lot.denomination = t["denomination"]
        lot.metal = t["metal"]
        lot.weight_g = round(rng.uniform(*t["weight"]), 2)
        lot.diameter_mm = round(rng.uniform(*t["diameter"]), 1)
        if lot.attribution_certain:
            lot.authority, lot.period = t["authority"], t["period"]
            lot.mint = t["mint"]
            lot.catalogue_ref = _catalogue_ref(t, rng)
        icon = ICONOGRAPHY[t["era"]]
        lot.obverse = rng.choice(icon["obverse"])
        lot.reverse = rng.choice(icon["reverse"])
        lot.legend = rng.choice(icon["legend"])
        lot.tags = ["silver"]

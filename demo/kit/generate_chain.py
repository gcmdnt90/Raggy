#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""generate_chain.py — the five handover artefacts of the demo chain.

The five demos are one story: D1 produces material D2 judges, D2 produces the
criteria D3 checks against the house documents, D3 produces the passage D4's
standing rules are written from, D4 produces the deliverable D5 attacks.

A chained narrative is a single point of failure: if D2 flops in the room, D3
has no input. So every handover file exists on disk BEFORE the lesson. A
successful live run overwrites it; a failed one is narrated and the pre-baked
file is opened instead. Nothing downstream ever waits on a live model.

These files are deliberately written as *model output*, not as ground truth:
they contain the same invented values, the same confident tone and (in d4) the
same single wrong row a live run produces. `LEGGIMI-CATENA.md` — trainer only —
says which one is wrong.

Run AFTER generate.py, on the same seed:

    python generate.py       --settore automazione
    python generate_chain.py --settore automazione

Adding a sector: add a block to CHAIN below. Everything else is read from
config/<settore>.json and from the generated folder, so the artefacts follow
the data instead of drifting from it.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# Per-sector material. Only what cannot be derived from the config or from the
# generated documents: the trade nouns, the four plausible-but-wrong values a
# model invents for each hole, and the human-verification list of D5.
# --------------------------------------------------------------------------
CHAIN = {
    "automazione": {
        "doc": "scheda di collaudo",
        "doc_pl": "schede di collaudo",
        "subject_key": "commessa",
        "truth_col": "order",
        "grade_prefix": "CE",
        "rules_doc": "regole/standard-collaudo.md",
        "guide_doc": "regole/guida-scala-esito.md",
        "holes": [
            ("codice articolo del PLC", "plc_article",
             ["6ES7214-1AG40-0XB0", "6ES7516-3AN02-0AB0",
              "6ES7215-1AG40-0XB0", "6ES7513-1AL02-0AB0"]),
            ("revisione della specifica di prova", "spec_ref",
             ["rev. A", "rev. 01", "rev. C", "rev. B"]),
            ("tipo di collaudo", "test_kind",
             ["FAT (in fabbrica)", "SAT (in sito)",
              "collaudo funzionale", "FAT (in fabbrica)"]),
            ("classe di esito", "grade",
             ["CE-1", "CE-2", "CE-2", "CE-1"]),
        ],
        "generic_answer": (
            "Nel collaudo di macchine automatiche si usano di norma le fasi FAT e SAT "
            "descritte dalla IEC 62381, con esito espresso come *passed / passed with "
            "deviations / failed* e una punch list allegata. La scheda riporta di solito "
            "identificativo della prova, criterio di accettazione, esito e firma delle parti."
        ),
        "generic_why_wrong": (
            "È l'impianto normativo del settore, e non è sbagliato in generale. "
            "Semplicemente non è il vostro: la casa usa una scala interna a cinque "
            "livelli che nessun modello può conoscere, e i campi obbligatori sono undici, "
            "non quattro."
        ),
        "human_checks": [
            "il codice articolo del PLC contro la targhetta o la distinta, mai contro la memoria del modello",
            "la revisione della specifica di prova contro il documento firmato",
            "la classe di esito ricalcolata a mano sul rapporto prove eseguite / prove totali",
            "il tempo ciclo misurato contro quello a contratto, con l'unità di misura",
            "la presenza della firma del cliente, o della dicitura che ne dichiara l'assenza",
            "che nessuna dichiarazione su funzioni di sicurezza o conformità CE sia finita nel testo",
        ],
    },
    "defi": {
        "doc": "scheda di rilascio",
        "doc_pl": "schede di rilascio",
        "subject_key": "rilascio",
        "truth_col": "reference",
        "grade_prefix": "RD",
        "rules_doc": "regole/standard-rilascio.md",
        "guide_doc": "regole/guida-scala-rilascio.md",
        "holes": [
            ("indirizzo del contratto", "contract_address",
             ["0x7a2f19c4b8e05d31a6f0c9b4e2d87a1f5c3b0e94",
              "0xc41d8b07e2f6a95310bd4e7c8a2f059d63b1e4a7",
              "0x3e9b5c1d07a8f24610cbe93d5f7a2b8c40d16e35",
              "0x9d0c4a7f1b3e825609fa1d7c4e0b93a852f61c08"]),
            ("commit di rilascio", "commit",
             ["9f3c1ab", "2ad4e07", "4e0c72f", "c18b5d3"]),
            ("riferimento della revisione esterna", "audit_ref",
             ["REV-2026-004", "AUD-2026-11", "REV-2026-012",
              "revisione esterna di giugno 2026"]),
            ("classe di rischio di rilascio", "grade",
             ["RD-1", "RD-2", "RD-2", "RD-1"]),
        ],
        "generic_answer": (
            "Nel rilascio di smart contract la gravità dei rilievi si esprime di norma con la "
            "scala delle società di revisione — Critical, High, Medium, Low, Informational — "
            "con riferimento allo SWC Registry per le classi di vulnerabilità e alle versioni "
            "delle librerie OpenZeppelin per le dipendenze. La checklist di rilascio riporta "
            "indirizzo, rete, verifica del sorgente sull'explorer, proprietà del proxy e "
            "parametri del timelock."
        ),
        "generic_why_wrong": (
            "È la tassonomia del settore, ed è corretta in generale. Semplicemente non è la "
            "vostra: la scala interna combina rilievi aperti, copertura dei test e finestra "
            "di timelock in un unico livello, e nessun modello può ricavarla — mentre i campi "
            "obbligatori della casa sono undici, non cinque."
        ),
        "human_checks": [
            "l'indirizzo del contratto contro l'explorer, carattere per carattere, mai contro la memoria del modello",
            "il commit di rilascio contro il tag firmato nel repository",
            "il riferimento della revisione esterna contro il report pubblicato, e NON DETERMINATO finché non lo è",
            "la classe di rischio ricalcolata a mano su rilievi aperti, copertura e timelock",
            "timelock e composizione del multisig verificati sulla catena, non sulla scheda",
            "che nessun rendimento atteso, storico o garantito sia finito nel testo",
            "che nessuna dichiarazione di conformità o di avvenuto audit sia finita nel testo",
        ],
    },
    "maglieria": {
        "doc": "scheda di specifica",
        "doc_pl": "schede di specifica",
        "subject_key": "specifica",
        "truth_col": "reference",
        "grade_prefix": "SP",
        "rules_doc": "regole/standard-specifica.md",
        "guide_doc": "regole/guida-scala-specifica.md",
        "holes": [
            ("modulo interessato e versione in esercizio", "module_ref",
             ["Pianificazione Produzione v3.2", "Modulo Programmazione 4.1",
              "Gestione Commesse v2.8", "Planning & Scheduling v3.0"]),
            ("codice cliente", "customer_code",
             ["CL-014", "MG-07", "CLI-2026-11", "C-0032"]),
            ("tempo standard della fase", "phase_std_min",
             ["circa 12 minuti a capo", "8 min/capo", "10–12 minuti a capo",
              "circa 15 minuti a capo"]),
            # Four confident industry figures. None of them is the measured one
            # on the survey, and two of them agree with what the capo reparto
            # said out loud — which is the point: the model reproduces the
            # hearsay, not the measurement.
            ("classe di specifica", "grade",
             ["SP-1", "SP-2", "SP-2", "SP-1"]),
        ],
        "generic_answer": (
            "Le richieste di modifica a un gestionale si classificano di norma con MoSCoW "
            "— Must, Should, Could, Won't — oppure con una matrice priorità/gravità, e si "
            "dimensionano in punti storia; i criteri di accettazione si scrivono in forma "
            "Given/When/Then e la scheda riporta descrizione, priorità, stima, criteri di "
            "accettazione e definition of done."
        ),
        "generic_why_wrong": (
            "È la pratica corrente della gestione requisiti, ed è corretta in generale. "
            "Semplicemente non è la vostra, e per una ragione precisa: MoSCoW e i punti "
            "storia misurano <b>priorità e dimensione</b>, mentre la scala SP misura quanta "
            "specifica manca ancora alla richiesta e chi deve firmarla. Nessun quadro di "
            "priorità ha un livello che dice «questo non deve diventare un ticket perché "
            "non è un problema di software»: il vostro SP-5 sì. E i campi obbligatori della "
            "casa sono undici, non cinque."
        ),
        "human_checks": [
            "il modulo e la versione in esercizio contro l'installato del committente, mai contro la memoria del modello",
            "il codice cliente contro l'anagrafica, e che il nome del maglificio non sia finito nella scheda",
            "il tempo standard della fase contro la rilevazione in reparto, con la data: un dato riferito a voce resta «dichiarato, non rilevato»",
            "la classe di specifica ricalcolata a mano su ambito, impatto sul modello dati e stato dei dati di processo, in quest'ordine",
            "che i criteri di accettazione siano almeno due e misurabili, altrimenti NON DEFINITI e stima NON STIMABILE",
            "che nessuna percentuale di miglioramento, di resa o di riduzione dei tempi sia finita nel testo",
            "che una richiesta di cambio processo sia uscita come SP-5 e non come stima",
        ],
    },
    "associazione": {
        "doc": "scheda quesito",
        "doc_pl": "schede quesito",
        "subject_key": "quesito",
        "truth_col": "reference",
        "grade_prefix": "UA",
        "rules_doc": "regole/regolamento-riscontro.md",
        "guide_doc": "regole/guida-scala-riscontro.md",
        "holes": [
            ("riferimento normativo", "norm_ref",
             ["art. 2118 del codice civile",
              "D.Lgs. 15 giugno 2015 n. 81, art. 19",
              "L. 20 maggio 1970 n. 300, art. 7",
              "CCNL di categoria, art. 42"]),
            ("contratto collettivo applicabile", "contract_ref",
             ["CCNL Artigianato Acconciatura ed Estetica",
              "CCNL Terziario, distribuzione e servizi",
              "CCNL Artigianato Area Meccanica",
              "CCNL Acconciatura ed Estetica (Confartigianato-CNA)"]),
            ("termine di riscontro", "deadline_days",
             ["45 giorni", "15 giorni", "entro 60 giorni", "20 giorni"]),
            ("classe di riscontro", "grade",
             ["UA-1", "UA-1", "UA-2", "UA-1"]),
        ],
        "generic_answer": (
            "Per un quesito di questo tipo si applica la disciplina del contratto collettivo "
            "di categoria e, per il rapporto di lavoro, il codice civile e il D.Lgs. 81/2015; "
            "il periodo di prova e il preavviso seguono le tabelle del CCNL applicato, e il "
            "riscontro all'associato va dato di norma entro trenta giorni."
        ),
        "generic_why_wrong": (
            "È diritto del lavoro italiano, ed è corretto in Italia. Non è il vostro: a San "
            "Marino la fonte è la legge sammarinese e i decreti delegati collegati, e il "
            "vostro regolamento dice che se la fonte sammarinese non è stata reperita la "
            "classe è UA-4 e il quesito esce dallo sportello — anche quando la fattispecie "
            "italiana è identica. Nessun modello sa che esiste una scala UA."
        ),
        "human_checks": [
            "la fonte citata contro il testo sammarinese in vigore, mai contro la memoria del modello",
            "che nessuna norma italiana sia rimasta nel riscontro come fonte applicabile",
            "il contratto collettivo applicabile contro quello depositato per quel settore",
            "importi, aliquote e minimi contrattuali contro la tabella in vigore, mai a memoria",
            "la classe di riscontro riassegnata da chi firma, con la regola del livello più alto in caso di dubbio",
            "che nella scheda non sia finito nessun dato personale dell'associato o dei suoi dipendenti",
            "che i quesiti su contenzioso aperto siano usciti come UA-5 e non come risposta nel merito",
        ],
    },
    "numismatica": {
        "doc": "scheda di catalogo",
        "doc_pl": "schede di catalogo",
        "subject_key": "lotto",
        "truth_col": "number",
        "grade_prefix": "SM",
        "rules_doc": "regole/regolamento-catalogazione.md",
        "guide_doc": "regole/guida-scala-conservazione.md",
        "holes": [
            ("riferimento bibliografico", "catalogue_ref",
             ["CNI XII, 45", "MIR 1042", "Biaggi 2231", "MEC 14, 812"]),
            ("zecca", "mint",
             ["Roma", "Milano", "Venezia", "Napoli"]),
            ("asse di conio", "die_axis",
             ["ore 6", "ore 12", "ore 6", "ore 9"]),
            ("conservazione", "grade",
             ["SM-2", "SM-1", "SM-2", "SM-3"]),
        ],
        "generic_answer": (
            "Le case d'asta usano in genere le scale di conservazione internazionali "
            "(FDC, SPL, BB, MB) oppure la scala Sheldon a 70 punti dei servizi di "
            "grading americani, e la descrizione riporta dritto, rovescio, metallo, "
            "peso e riferimento di catalogo."
        ),
        "generic_why_wrong": (
            "È il vocabolario del mestiere, e non è sbagliato in generale. Semplicemente "
            "non è il vostro: la casa usa una scala interna a cinque livelli che nessun "
            "modello può conoscere, e il regolamento impone campi che quelle scale non "
            "prevedono."
        ),
        "human_checks": [
            "il riferimento bibliografico contro il repertorio cartaceo, mai contro la memoria del modello",
            "la zecca e l'anno contro l'esemplare, o la dicitura NON DETERMINATO",
            "il peso contro una seconda pesata, quando la prima è annotata come da ricontrollare",
            "la conservazione riassegnata a vista dal perito",
            "la provenienza: se non è documentata, resta non documentata",
            "che nessuna stima di prezzo o attribuzione automatica sia finita nel testo",
        ],
    },
    "fotovoltaico": {
        "doc": "scheda di impianto",
        "doc_pl": "schede di impianto",
        "subject_key": "impianto",
        "truth_col": "reference",
        "grade_prefix": "RG",
        "rules_doc": "regole/istruzione-monitoraggio.md",
        "guide_doc": "regole/guida-scala-rendimento.md",
        "holes": [
            ("codice pratica", "reference",
             ["GSE-2026-0417", "PR-RSM-2026-88", "SM-FV-2026-114", "GAUDI-4471902"]),
            ("performance ratio", "pr_percent",
             ["81,4 %", "78,0 %", "84,2 %", "79,5 %"]),
            ("ore equivalenti", "equivalent_hours",
             ["122", "118", "130", "121"]),
            ("classe di rendimento", "grade",
             ["RG-2", "RG-1", "RG-2", "RG-3"]),
        ],
        "generic_answer": (
            "Il rendimento di un impianto fotovoltaico si esprime con il performance "
            "ratio definito dalla IEC 61724-1, di norma con soglie indicative attorno "
            "all'80 % per impianti in buono stato, e la scheda riporta produzione, "
            "irraggiamento, ore equivalenti e fermi."
        ),
        "generic_why_wrong": (
            "È la definizione di riferimento del settore, e non è sbagliata in generale. "
            "Semplicemente non è la vostra: la casa usa una scala interna a cinque livelli "
            "con soglie proprie, e la pratica sammarinese non è quella italiana."
        ),
        "human_checks": [
            "il codice pratica contro il fascicolo, mai contro la memoria del modello",
            "la lettura di produzione contro il contatore, quando è annotata come di fine mese",
            "il performance ratio ricalcolato a mano su produzione e irraggiamento",
            "l'autoconsumo: se è dichiarato dal cliente e non misurato, resta dichiarato",
            "la classe di rendimento riassegnata dal tecnico",
            "che nessun riferimento a incentivi italiani sia finito in una pratica sammarinese",
        ],
    },
}

TOOLS = ["ChatGPT", "ChatGPT (rigenerato)", "Claude", "Claude (rigenerato)"]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def load_truth(out: Path, col: str, value: str) -> dict:
    """The row of ground-truth.csv the raw notes describe."""
    path = out / "_perito" / "ground-truth.csv"
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if str(row.get(col, "")).strip() == str(value).strip():
                return row
    raise SystemExit(f"ground-truth.csv: nessuna riga con {col} = {value}")


def all_rows(out: Path) -> list[dict]:
    with (out / "_perito" / "ground-truth.csv").open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def header(title: str, produced_in: str, sub: str) -> str:
    return (
        f"# {title}\n\n"
        f"> **Copia di riserva.** Prodotto in aula durante {produced_in}. "
        f"Se l'esecuzione dal vivo è andata a buon fine, questo file va sostituito "
        f"con quella; se non è andata, si apre questo e la catena prosegue.\n"
        f"> {sub}\n\n"
    )


def frontmatter(demo: str, produces: str, consumed_by: str) -> str:
    return (
        "---\n"
        f"catena: {demo}\n"
        f"prodotto_da: {demo}\n"
        f"consumato_da: {consumed_by}\n"
        f"file: {produces}\n"
        f"generato: {date.today().isoformat()}\n"
        "---\n\n"
    )


# --------------------------------------------------------------------------
# the five artefacts
# --------------------------------------------------------------------------
def d1(cfg, sec, grezzi, truth) -> str:
    subject = grezzi.get(sec["subject_key"])
    doc = sec["doc"]
    out = [frontmatter("D1", "d1-bozze.md", "D2, D4")]
    out.append(header(
        f"D1 — Quattro bozze della stessa {doc}",
        "il modulo 1",
        f"Stesso prompt, quattro esecuzioni: due strumenti, una rigenerazione ciascuno. "
        f"Nessuna regola permanente attiva. Fonte: `demo/m4-grezzi.md` — appunti grezzi di **{subject}**.",
    ))
    out.append(
        "Le quattro bozze sono leggibili, professionali e pronte da consegnare.\n"
        "Nessuna delle quattro dichiara che cosa ha inventato.\n\n"
    )
    for i, tool in enumerate(TOOLS):
        out.append(f"## Bozza {i + 1} — {tool}\n\n")
        lines = []
        for label, _col, values in sec["holes"]:
            lines.append(f"- **{label}:** {values[i]}")
        for k, v in list(grezzi.items())[:6]:
            if v is None or k == sec["subject_key"]:
                continue
            lines.append(f"- {k.replace('_', ' ')}: {v}")
        out.append("\n".join(lines) + "\n\n")
    out.append("## Che cosa non era negli appunti\n\n")
    cols = " | ".join(f"bozza {i + 1}" for i in range(4))
    out.append(f"| campo | negli appunti | {cols} |\n")
    out.append("|---|---|" + "---|" * 4 + "\n")
    for label, col, values in sec["holes"]:
        cells = " | ".join(values)
        out.append(f"| {label} | *vuoto* | {cells} |\n")
    out.append(
        f"\n**Il valore vero,** per chi lo può verificare: "
        + ", ".join(
            f"{label} = `{truth.get(col, 'n.d.')}`" for label, col, _v in sec["holes"]
        )
        + ".\n\n"
        "Quattro esecuzioni, quattro valori diversi, nessun avviso. "
        "Questo file è il riferimento «senza regole» del modulo 4: non va rieseguito, va riaperto.\n"
    )
    return "".join(out)


def d2(cfg, sec, grezzi) -> str:
    doc = sec["doc"]
    fields = cfg.get("mandatory_fields", [])
    out = [frontmatter("D2", "d2-criteri.md", "D3, D4")]
    out.append(header(
        "D2 — I criteri, come li scrive il modello",
        "il modulo 2",
        f"Le quattro bozze di `d1-bozze.md` date da giudicare allo stesso modello a due "
        f"livelli di capacità, poi con il ragionamento esteso acceso.",
    ))
    out.append(
        "## Giudizio del modello piccolo\n\n"
        "> La bozza 3 è la più completa e la più chiara. La consiglierei per la consegna: "
        "il linguaggio è professionale e tutti i campi risultano compilati.\n\n"
        "Sceglie, non argomenta. «Tutti i campi risultano compilati» è vero e non significa nulla: "
        "sono compilati perché sono stati inventati.\n\n"
        "## Giudizio del modello grande, ragionamento esteso\n\n"
        f"> Le quattro bozze divergono su quattro campi. Prima di scegliere serve stabilire "
        f"che cosa rende accettabile una {doc}. I criteri che userei:\n\n"
    )
    invented = [
        "ogni campo compilato deve essere tracciabile a un dato in ingresso",
        "un campo non ricavabile dagli appunti va lasciato vuoto e segnalato, non stimato",
        "le unità di misura vanno riportate accanto al valore",
        "i giudizi di sintesi vanno separati dai dati osservati",
        "la stessa domanda deve dare la stessa risposta a distanza di un'ora",
        "il documento deve dire chi lo ha redatto e quando",
        "chi firma deve poter rifare il calcolo senza rileggere gli appunti",
    ]
    out.append("\n".join(f"{i + 1}. {c}" for i, c in enumerate(invented)) + "\n\n")
    out.append(
        "> Quello che non posso verificare: se esista un formato interno obbligatorio, "
        "quali campi la casa consideri non omissibili, e con quale scala si esprime l'esito.\n\n"
        "## Criteri accettati in aula\n\n"
        "_Da rivedere con la persona in aula: cancellare, aggiungere, riordinare. "
        "Questa lista entra in D3, dove si confronta con quello che i documenti dicono davvero._\n\n"
    )
    out.append("\n".join(f"- [ ] {c}" for c in invented) + "\n\n")
    if fields:
        out.append(
            f"> Per il formatore: i campi obbligatori scritti nel regolamento della casa sono "
            f"**{len(fields)}**. La lista qui sopra ne indovina "
            f"{'due o tre' if len(fields) > 4 else 'una parte'}. Il resto è il salto del modulo 3.\n"
        )
    return "".join(out)


def d3(cfg, sec, grezzi) -> str:
    out = [frontmatter("D3", "d3-fonte.md", "D4")]
    out.append(header(
        "D3 — Il criterio esiste già, ed è scritto",
        "il modulo 3",
        "La stessa domanda sui tre gradini della scala. Il gradino 1 non ha documenti, "
        "i gradini 2 e 3 hanno gli stessi file di `regole/`.",
    ))
    out.append("## Gradino 1 — chat semplice, nessun documento\n\n")
    out.append("> " + sec["generic_answer"].replace("\n", "\n> ") + "\n\n")
    out.append(
        "È la risposta più fluente delle tre, ed è quella sbagliata. "
        + sec["generic_why_wrong"] + "\n\n"
    )
    out.append("## Gradini 2 e 3 — con i documenti della casa\n\n")
    grades = cfg.get("grades", [])
    if grades:
        out.append("La scala interna, dal documento:\n\n")
        for g in grades:
            out.append(f"- **{g['code']} — {g['label']}**: {g['definition']}\n")
        out.append("\n")
    fields = cfg.get("mandatory_fields", [])
    if fields:
        out.append(f"I campi obbligatori, dal documento — sono {len(fields)}:\n\n")
        out.append("\n".join(f"{i + 1}. {f}" for i, f in enumerate(fields)) + "\n\n")
    out.append(
        f"**Passaggio recuperato:** `{sec['rules_doc']}`, sezioni 1 e 2 — "
        f"più `{sec['guide_doc']}` per la regola del dubbio fra due livelli adiacenti.\n\n"
        "## Delta rispetto a D2\n\n"
        "| criterio inventato in D2 | c'è nei documenti? |\n|---|---|\n"
        "| tracciabilità del campo compilato | sì, in forma più dura: campo vuoto **o** dicitura esplicita |\n"
        "| unità di misura accanto al valore | sì, implicito nei campi obbligatori |\n"
        "| separare giudizi e dati osservati | sì, ed è una regola di redazione, non un consiglio |\n"
        "| stessa risposta a distanza di un'ora | no — non è un criterio della casa |\n"
        "| chi ha redatto e quando | sì, ed è obbligatorio |\n"
        "| la scala di esito | **no, e non era indovinabile** |\n"
        "| i campi non omissibili | **no, e non erano indovinabili** |\n\n"
        "Il modello aveva ragione su una parte, e le parti su cui aveva torto le avrebbe "
        "scritte con la stessa sicurezza.\n\n"
        "## Ramo morto\n\n"
        "La domanda con le parole sbagliate (`m3-p5`) chiede una cosa che i documenti non "
        "coprono. Il recupero restituisce comunque i passaggi più vicini, e la risposta arriva "
        "lo stesso. Non produce niente per il modulo 4: serve solo a far vedere che *una "
        "risposta* non è *la risposta*.\n"
    )
    return "".join(out)


def d4(cfg, sec, out_dir) -> str:
    rows = all_rows(out_dir)
    out = [frontmatter("D4", "d4-tabella.md", "D5")]
    out.append(header(
        f"D4 — La tabella delle {sec['doc_pl']}",
        "il modulo 4",
        "Prodotto dall'agente sulla cartella dei documenti, con le regole permanenti attive "
        "e i criteri dichiarati prima della generazione.",
    ))
    labels = {
        "reference": "riferimento", "order": "commessa", "site": "sito",
        "vault": "vault", "chain": "rete", "contract_address": "indirizzo",
        "coverage_percent": "copertura (%)", "category": "categoria",
        "member_sector": "settore associato", "norm_ref": "fonte citata",
        "members_affected": "associati",
        "customer_code": "cliente", "module": "modulo", "phase": "fase",
        "process_data": "dati di processo", "data_impact": "impatto sui dati",
        "capi_month": "capi/mese",
        "machine": "macchina", "denomination": "nominale", "metal": "metallo",
        "weight_g": "peso (g)", "tests_done": "prove eseguite",
        "tests_total": "prove totali", "cycle_time_s": "tempo ciclo (s)",
        "kwh": "produzione (kWh)", "pr_percent": "performance ratio (%)",
        "grade": "classe", "operator": "operatore",
    }
    keys = [k for k in ("reference", "order", "site", "machine", "denomination",
                        "metal", "weight_g", "vault", "chain", "contract_address",
                        "category", "member_sector", "norm_ref",
                        "customer_code", "module", "phase",
                        "tests_done", "tests_total", "kwh",
                        "cycle_time_s", "pr_percent", "coverage_percent",
                        "members_affected", "capi_month",
                        "process_data", "data_impact", "grade", "operator")
            if rows and k in rows[0]]
    out.append("| " + " | ".join(labels[k] for k in keys) + " |\n")
    out.append("|" + "---|" * len(keys) + "\n")
    for i, r in enumerate(rows):
        cells = [r.get(k, "") for k in keys]
        # The deliberate error: one row carries a grade one level off, with no
        # flag on it. DEMO-CHECKLIST failure #2 must survive a good model.
        if i == 4 and "grade" in keys:
            g = r.get("grade", "")
            if g and g[-1].isdigit():
                cells[keys.index("grade")] = f"{g[:-1]}{max(1, int(g[-1]) - 1)}"
        out.append("| " + " | ".join(str(c) for c in cells) + " |\n")
    out.append(
        "\n**Campi lasciati vuoti dalle regole permanenti:** i campi non ricavabili dai "
        "documenti portano la dicitura DA VERIFICARE e non un valore.\n\n"
        "> Per il formatore: **una riga di questa tabella è sbagliata** e non è segnalata. "
        "Vedi `LEGGIMI-CATENA.md`. È il fallimento voluto n. 2: si coglie in pubblico, "
        "aprendo il documento di origine accanto a `_perito/ground-truth.csv`.\n"
    )
    return "".join(out)


def d5(cfg, sec) -> str:
    out = [frontmatter("D5", "d5-verifiche-umane.md", "chiusura")]
    out.append(header(
        "D5 — Che cosa deve controllare una persona",
        "il modulo 5",
        "La lista è il collaudo del collaudo: quello che resta in capo a chi firma, "
        "dopo che tutto il resto è stato automatizzato.",
    ))
    out.append("## Prima che il documento esca\n\n")
    out.append("\n".join(f"- [ ] {c}" for c in sec["human_checks"]) + "\n\n")
    out.append(
        "## Perché queste e non altre\n\n"
        "| visto in aula | che cosa insegna |\n|---|---|\n"
        "| quattro bozze, quattro valori diversi (D1) | la fluidità non è accuratezza |\n"
        "| il modello non conosceva la scala interna (D3) | senza documenti risponde con la media del settore |\n"
        "| le regole in prosa non hanno bloccato la richiesta (D4) | i limiti duri stanno fuori dal modello |\n"
        "| una riga sbagliata su dodici (D4) | il controllo va fatto contro la fonte, non contro il risultato |\n"
        "| il documento avvelenato (D5-B) | testo e istruzioni arrivano dallo stesso canale |\n"
        "| l'attribuzione a freddo smontata (D5-C) | la sicurezza dichiarata non è una misura di affidabilità |\n\n"
        "## Che cosa resta in mano\n\n"
        "1. le regole permanenti scritte in aula\n"
        "2. la tabella prodotta dall'agente, con una riga da correggere\n"
        "3. questa lista\n"
    )
    return "".join(out)


def readme(sec, truth, out_dir) -> str:
    rows = all_rows(out_dir)
    bad = rows[4] if len(rows) > 4 else {}
    return (
        "# Catena delle demo — note per il formatore\n\n"
        "**Non proiettare questo file.**\n\n"
        "I cinque file di questa cartella sono le copie di riserva della catena: "
        "D1 produce per D2, D2 per D3, D3 per D4, D4 per D5. Ogni esecuzione dal vivo "
        "riuscita sostituisce il file corrispondente; ogni esecuzione fallita si racconta "
        "e si apre il file. La catena non si ferma mai.\n\n"
        "| file | prodotto in | consumato da |\n|---|---|---|\n"
        "| `d1-bozze.md` | D1 (M1) | D2, e come riferimento «senza regole» in D4 |\n"
        "| `d2-criteri.md` | D2 (M2) | D3, e come materia delle regole in D4 |\n"
        "| `d3-fonte.md` | D3 (M3) | D4 |\n"
        "| `d4-tabella.md` | D4 (M4) | D5 |\n"
        "| `d5-verifiche-umane.md` | D5 (M5) | la chiusura |\n\n"
        "## La riga sbagliata di d4-tabella.md\n\n"
        f"Riga **5** — `{bad.get('reference', '?')}`: la classe è abbassata di un livello "
        f"rispetto a `_perito/ground-truth.csv`, che dice `{bad.get('grade', '?')}`. "
        "Nessun contrassegno la segnala. È il fallimento voluto n. 2 della DEMO-CHECKLIST: "
        "va colto in pubblico aprendo il documento di origine accanto alla tabella.\n\n"
        "## I valori veri del record di D1\n\n"
        + "".join(
            f"- {label}: `{truth.get(col, 'n.d.')}`\n" for label, col, _v in sec["holes"]
        )
        + "\nRigenerando i dati con lo stesso seed questi valori non cambiano. "
        "Se cambi il seed, rilancia anche `generate_chain.py`.\n"
    )


# --------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--settore", required=True, choices=sorted(CHAIN))
    ap.add_argument("--out", help="cartella generata (default: quella del config)")
    args = ap.parse_args()

    cfg = json.loads((ROOT / "config" / f"{args.settore}.json").read_text(encoding="utf-8"))
    sec = CHAIN[args.settore]
    out_dir = Path(args.out) if args.out else (ROOT / "config" / cfg["output"]).resolve()
    if not out_dir.exists():
        raise SystemExit(f"{out_dir} non esiste — lancia prima generate.py")

    grezzi = json.loads((out_dir / "demo" / "m4-grezzi.json").read_text(encoding="utf-8"))
    truth = load_truth(out_dir, sec["truth_col"], grezzi[sec["subject_key"]])

    dest = out_dir / "demo" / "catena"
    dest.mkdir(parents=True, exist_ok=True)
    files = {
        "d1-bozze.md": d1(cfg, sec, grezzi, truth),
        "d2-criteri.md": d2(cfg, sec, grezzi),
        "d3-fonte.md": d3(cfg, sec, grezzi),
        "d4-tabella.md": d4(cfg, sec, out_dir),
        "d5-verifiche-umane.md": d5(cfg, sec),
        "LEGGIMI-CATENA.md": readme(sec, truth, out_dir),
    }
    for name, text in files.items():
        (dest / name).write_text(text, encoding="utf-8")
        print(f"  {dest.relative_to(out_dir.parent)}/{name}")
    print(f"[{args.settore}] catena: {len(files)} file.")


if __name__ == "__main__":
    main()

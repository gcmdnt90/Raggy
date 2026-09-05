---
catena: D1
prodotto_da: D1
consumato_da: D2, D4
file: d1-bozze.md
generato: 2026-09-03
---

# D1 — Quattro bozze della stessa scheda di collaudo

> **Copia di riserva.** Prodotto in aula durante il modulo 1. Se l'esecuzione dal vivo è andata a buon fine, questo file va sostituito con quella; se non è andata, si apre questo e la catena prosegue.
> Stesso prompt, quattro esecuzioni: due strumenti, una rigenerazione ciascuno. Nessuna regola permanente attiva. Fonte: `demo/m4-grezzi.md` — appunti grezzi di **CEL-39**.

Le quattro bozze sono leggibili, professionali e pronte da consegnare.
Nessuna delle quattro dichiara che cosa ha inventato.

## Bozza 1 — ChatGPT

- **codice articolo del PLC:** 6ES7214-1AG40-0XB0
- **revisione della specifica di prova:** rev. A
- **tipo di collaudo:** FAT (in fabbrica)
- **classe di esito:** CE-1
- macchina: Cella di asservimento torni
- software: PLC/HMI V3.7.4, consegnato a inizio settimana
- specifica di prova: SPC-2026-082

## Bozza 2 — ChatGPT (rigenerato)

- **codice articolo del PLC:** 6ES7516-3AN02-0AB0
- **revisione della specifica di prova:** rev. 01
- **tipo di collaudo:** SAT (in sito)
- **classe di esito:** CE-2
- macchina: Cella di asservimento torni
- software: PLC/HMI V3.7.4, consegnato a inizio settimana
- specifica di prova: SPC-2026-082

## Bozza 3 — Claude

- **codice articolo del PLC:** 6ES7215-1AG40-0XB0
- **revisione della specifica di prova:** rev. C
- **tipo di collaudo:** collaudo funzionale
- **classe di esito:** CE-2
- macchina: Cella di asservimento torni
- software: PLC/HMI V3.7.4, consegnato a inizio settimana
- specifica di prova: SPC-2026-082

## Bozza 4 — Claude (rigenerato)

- **codice articolo del PLC:** 6ES7513-1AL02-0AB0
- **revisione della specifica di prova:** rev. B
- **tipo di collaudo:** FAT (in fabbrica)
- **classe di esito:** CE-1
- macchina: Cella di asservimento torni
- software: PLC/HMI V3.7.4, consegnato a inizio settimana
- specifica di prova: SPC-2026-082

## Che cosa non era negli appunti

| campo | negli appunti | bozza 1 | bozza 2 | bozza 3 | bozza 4 |
|---|---|---|---|---|---|
| codice articolo del PLC | *vuoto* | 6ES7214-1AG40-0XB0 | 6ES7516-3AN02-0AB0 | 6ES7215-1AG40-0XB0 | 6ES7513-1AL02-0AB0 |
| revisione della specifica di prova | *vuoto* | rev. A | rev. 01 | rev. C | rev. B |
| tipo di collaudo | *vuoto* | FAT (in fabbrica) | SAT (in sito) | collaudo funzionale | FAT (in fabbrica) |
| classe di esito | *vuoto* | CE-1 | CE-2 | CE-2 | CE-1 |

**Il valore vero,** per chi lo può verificare: codice articolo del PLC = `6ES7516-6HG40-0AB0`, revisione della specifica di prova = `SPC-2026-082 rev. B`, tipo di collaudo = `FAT (in fabbrica)`, classe di esito = `CE-3`.

Quattro esecuzioni, quattro valori diversi, nessun avviso. Questo file è il riferimento «senza regole» del modulo 4: non va rieseguito, va riaperto.

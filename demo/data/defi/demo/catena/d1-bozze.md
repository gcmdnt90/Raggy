---
catena: D1
prodotto_da: D1
consumato_da: D2, D4
file: d1-bozze.md
generato: 2026-09-12
---

# D1 — Quattro bozze della stessa scheda di rilascio

> **Copia di riserva.** Prodotto in aula durante il modulo 1. Se l'esecuzione dal vivo è andata a buon fine, questo file va sostituito con quella; se non è andata, si apre questo e la catena prosegue.
> Stesso prompt, quattro esecuzioni: due strumenti, una rigenerazione ciascuno. Nessuna regola permanente attiva. Fonte: `demo/m4-grezzi.md` — appunti grezzi di **RIL-2026-001**.

Le quattro bozze sono leggibili, professionali e pronte da consegnare.
Nessuna delle quattro dichiara che cosa ha inventato.

## Bozza 1 — ChatGPT

- **indirizzo del contratto:** 0x7a2f19c4b8e05d31a6f0c9b4e2d87a1f5c3b0e94
- **commit di rilascio:** 9f3c1ab
- **riferimento della revisione esterna:** REV-2026-004
- **classe di rischio di rilascio:** RD-1
- vault: USDC — liquidità su pool stabile
- strategia: v3.7.7, congelata da 21 giorni
- rete: Base
- copertura test percento: 72.8
- rilievi alti: 1

## Bozza 2 — ChatGPT (rigenerato)

- **indirizzo del contratto:** 0xc41d8b07e2f6a95310bd4e7c8a2f059d63b1e4a7
- **commit di rilascio:** 2ad4e07
- **riferimento della revisione esterna:** AUD-2026-11
- **classe di rischio di rilascio:** RD-2
- vault: USDC — liquidità su pool stabile
- strategia: v3.7.7, congelata da 21 giorni
- rete: Base
- copertura test percento: 72.8
- rilievi alti: 1

## Bozza 3 — Claude

- **indirizzo del contratto:** 0x3e9b5c1d07a8f24610cbe93d5f7a2b8c40d16e35
- **commit di rilascio:** 4e0c72f
- **riferimento della revisione esterna:** REV-2026-012
- **classe di rischio di rilascio:** RD-2
- vault: USDC — liquidità su pool stabile
- strategia: v3.7.7, congelata da 21 giorni
- rete: Base
- copertura test percento: 72.8
- rilievi alti: 1

## Bozza 4 — Claude (rigenerato)

- **indirizzo del contratto:** 0x9d0c4a7f1b3e825609fa1d7c4e0b93a852f61c08
- **commit di rilascio:** c18b5d3
- **riferimento della revisione esterna:** revisione esterna di giugno 2026
- **classe di rischio di rilascio:** RD-1
- vault: USDC — liquidità su pool stabile
- strategia: v3.7.7, congelata da 21 giorni
- rete: Base
- copertura test percento: 72.8
- rilievi alti: 1

## Che cosa non era negli appunti

| campo | negli appunti | bozza 1 | bozza 2 | bozza 3 | bozza 4 |
|---|---|---|---|---|---|
| indirizzo del contratto | *vuoto* | 0x7a2f19c4b8e05d31a6f0c9b4e2d87a1f5c3b0e94 | 0xc41d8b07e2f6a95310bd4e7c8a2f059d63b1e4a7 | 0x3e9b5c1d07a8f24610cbe93d5f7a2b8c40d16e35 | 0x9d0c4a7f1b3e825609fa1d7c4e0b93a852f61c08 |
| commit di rilascio | *vuoto* | 9f3c1ab | 2ad4e07 | 4e0c72f | c18b5d3 |
| riferimento della revisione esterna | *vuoto* | REV-2026-004 | AUD-2026-11 | REV-2026-012 | revisione esterna di giugno 2026 |
| classe di rischio di rilascio | *vuoto* | RD-1 | RD-2 | RD-2 | RD-1 |

**Il valore vero,** per chi lo può verificare: indirizzo del contratto = `0xe1e26a7c5491c4fe33fae9b28f310c208f8b84b4`, commit di rilascio = `b78ddaa`, riferimento della revisione esterna = `REV-2026-009`, classe di rischio di rilascio = `RD-4`.

Quattro esecuzioni, quattro valori diversi, nessun avviso. Questo file è il riferimento «senza regole» del modulo 4: non va rieseguito, va riaperto.

# Catena delle demo — note per il formatore

**Non proiettare questo file.**

I cinque file di questa cartella sono le copie di riserva della catena: D1 produce per D2, D2 per D3, D3 per D4, D4 per D5. Ogni esecuzione dal vivo riuscita sostituisce il file corrispondente; ogni esecuzione fallita si racconta e si apre il file. La catena non si ferma mai.

| file | prodotto in | consumato da |
|---|---|---|
| `d1-bozze.md` | D1 (M1) | D2, e come riferimento «senza regole» in D4 |
| `d2-criteri.md` | D2 (M2) | D3, e come materia delle regole in D4 |
| `d3-fonte.md` | D3 (M3) | D4 |
| `d4-tabella.md` | D4 (M4) | D5 |
| `d5-verifiche-umane.md` | D5 (M5) | la chiusura |

## La riga sbagliata di d4-tabella.md

Riga **5** — `CLD-2026-005`: la classe è abbassata di un livello rispetto a `_perito/ground-truth.csv`, che dice `CE-4`. Nessun contrassegno la segnala. È il fallimento voluto n. 2 della DEMO-CHECKLIST: va colto in pubblico aprendo il documento di origine accanto alla tabella.

## I valori veri del record di D1

- codice articolo del PLC: `6ES7516-6HG40-0AB0`
- revisione della specifica di prova: `SPC-2026-082 rev. B`
- tipo di collaudo: `FAT (in fabbrica)`
- classe di esito: `CE-3`

Rigenerando i dati con lo stesso seed questi valori non cambiano. Se cambi il seed, rilancia anche `generate_chain.py`.

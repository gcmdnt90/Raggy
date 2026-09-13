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

Riga **5** — `RIL-2026-005`: la classe è abbassata di un livello rispetto a `_perito/ground-truth.csv`, che dice `RD-5`. Nessun contrassegno la segnala. È il fallimento voluto n. 2 della DEMO-CHECKLIST: va colto in pubblico aprendo il documento di origine accanto alla tabella.

## I valori veri del record di D1

- indirizzo del contratto: `0xe1e26a7c5491c4fe33fae9b28f310c208f8b84b4`
- commit di rilascio: `b78ddaa`
- riferimento della revisione esterna: `REV-2026-009`
- classe di rischio di rilascio: `RD-4`

Rigenerando i dati con lo stesso seed questi valori non cambiano. Se cambi il seed, rilancia anche `generate_chain.py`.

# Guida rapida alla scala RD

*Promemoria operativo per lo staff. Estratto del regolamento, sezione 1.*

In caso di dubbio fra due livelli adiacenti si assegna sempre il livello **più alto**, cioè il più prudente. Il dubbio va annotato nel campo note.

## RD-1 — Rilascio diretto

Nessun rilievo critico o alto aperto, copertura dei test pari o superiore all'85% e timelock di almeno 48 ore: il rilascio procede con la firma di un solo revisore.

## RD-2 — Rilascio sorvegliato

Nessun rilievo critico, al più un rilievo alto già chiuso o tre rilievi medi: il rilascio procede con monitoraggio giornaliero per sette giorni.

## RD-3 — Rilascio limitato

Nessun rilievo critico aperto ma timelock inferiore a 48 ore oppure copertura dei test sotto l'85%: si rilascia con esposizione massima ridotta e monitoraggio per quattordici giorni.

## RD-4 — Rilascio sospeso

Almeno un rilievo alto aperto, oppure copertura dei test sotto il 70%: serve la firma di un secondo revisore e la richiusura del rilievo prima della messa in rete.

## RD-5 — Non rilasciabile

Rilievo critico aperto, oppure commit di rilascio non tracciato: la scheda non può essere chiusa e il rilascio non entra in rete principale.

## Errori frequenti

- Assegnare RD-1 quando non ci sono rilievi ma la copertura dei test è sotto l'85%: la copertura entra nella classe.
- Usare RD-5 come sinonimo di «contratto vulnerabile»: RD-5 indica una scheda che non può essere chiusa, anche solo per un commit non tracciato.
- Riportare il riferimento di una revisione esterna non ancora pubblicata: finché non è pubblica si scrive NON DETERMINATO.
- Omettere la classe quando l'esito non è confermato: i due campi sono indipendenti.

---

_Documento sintetico generato per formazione — non usare in produzione._

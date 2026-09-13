---
catena: D3
prodotto_da: D3
consumato_da: D4
file: d3-fonte.md
generato: 2026-09-12
---

# D3 — Il criterio esiste già, ed è scritto

> **Copia di riserva.** Prodotto in aula durante il modulo 3. Se l'esecuzione dal vivo è andata a buon fine, questo file va sostituito con quella; se non è andata, si apre questo e la catena prosegue.
> La stessa domanda sui tre gradini della scala. Il gradino 1 non ha documenti, i gradini 2 e 3 hanno gli stessi file di `regole/`.

## Gradino 1 — chat semplice, nessun documento

> Nel rilascio di smart contract la gravità dei rilievi si esprime di norma con la scala delle società di revisione — Critical, High, Medium, Low, Informational — con riferimento allo SWC Registry per le classi di vulnerabilità e alle versioni delle librerie OpenZeppelin per le dipendenze. La checklist di rilascio riporta indirizzo, rete, verifica del sorgente sull'explorer, proprietà del proxy e parametri del timelock.

È la risposta più fluente delle tre, ed è quella sbagliata. È la tassonomia del settore, ed è corretta in generale. Semplicemente non è la vostra: la scala interna combina rilievi aperti, copertura dei test e finestra di timelock in un unico livello, e nessun modello può ricavarla — mentre i campi obbligatori della casa sono undici, non cinque.

## Gradini 2 e 3 — con i documenti della casa

La scala interna, dal documento:

- **RD-1 — Rilascio diretto**: Nessun rilievo critico o alto aperto, copertura dei test pari o superiore all'85% e timelock di almeno 48 ore: il rilascio procede con la firma di un solo revisore.
- **RD-2 — Rilascio sorvegliato**: Nessun rilievo critico, al più un rilievo alto già chiuso o tre rilievi medi: il rilascio procede con monitoraggio giornaliero per sette giorni.
- **RD-3 — Rilascio limitato**: Nessun rilievo critico aperto ma timelock inferiore a 48 ore oppure copertura dei test sotto l'85%: si rilascia con esposizione massima ridotta e monitoraggio per quattordici giorni.
- **RD-4 — Rilascio sospeso**: Almeno un rilievo alto aperto, oppure copertura dei test sotto il 70%: serve la firma di un secondo revisore e la richiusura del rilievo prima della messa in rete.
- **RD-5 — Non rilasciabile**: Rilievo critico aperto, oppure commit di rilascio non tracciato: la scheda non può essere chiusa e il rilascio non entra in rete principale.

I campi obbligatori, dal documento — sono 11:

1. riferimento interno di rilascio (formato RIL-<anno>-<numero>)
2. nome del vault o della strategia e versione, nel formato vX.Y.Z
3. rete di destinazione e indirizzo del contratto, oppure la dicitura NON DETERMINATO
4. commit di rilascio in forma abbreviata a sette caratteri, oppure NON ANNOTATO
5. dipendenza esterna con la versione dichiarata nel lockfile, oppure NON ANNOTATA
6. rilievi aperti divisi per gravità, con il numero per ciascun livello
7. copertura dei test in percentuale, con una cifra decimale
8. finestra di timelock in ore e composizione del multisig
9. esposizione massima prevista nella prima settimana, in dollari
10. classe di rischio di rilascio della scala interna RD-1 / RD-5
11. riferimento della revisione esterna pubblicata, oppure la dicitura NON DETERMINATO

**Passaggio recuperato:** `regole/standard-rilascio.md`, sezioni 1 e 2 — più `regole/guida-scala-rilascio.md` per la regola del dubbio fra due livelli adiacenti.

## Delta rispetto a D2

| criterio inventato in D2 | c'è nei documenti? |
|---|---|
| tracciabilità del campo compilato | sì, in forma più dura: campo vuoto **o** dicitura esplicita |
| unità di misura accanto al valore | sì, implicito nei campi obbligatori |
| separare giudizi e dati osservati | sì, ed è una regola di redazione, non un consiglio |
| stessa risposta a distanza di un'ora | no — non è un criterio della casa |
| chi ha redatto e quando | sì, ed è obbligatorio |
| la scala di esito | **no, e non era indovinabile** |
| i campi non omissibili | **no, e non erano indovinabili** |

Il modello aveva ragione su una parte, e le parti su cui aveva torto le avrebbe scritte con la stessa sicurezza.

## Ramo morto

La domanda con le parole sbagliate (`m3-p5`) chiede una cosa che i documenti non coprono. Il recupero restituisce comunque i passaggi più vicini, e la risposta arriva lo stesso. Non produce niente per il modulo 4: serve solo a far vedere che *una risposta* non è *la risposta*.

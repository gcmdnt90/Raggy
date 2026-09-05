---
catena: D3
prodotto_da: D3
consumato_da: D4
file: d3-fonte.md
generato: 2026-09-03
---

# D3 — Il criterio esiste già, ed è scritto

> **Copia di riserva.** Prodotto in aula durante il modulo 3. Se l'esecuzione dal vivo è andata a buon fine, questo file va sostituito con quella; se non è andata, si apre questo e la catena prosegue.
> La stessa domanda sui tre gradini della scala. Il gradino 1 non ha documenti, i gradini 2 e 3 hanno gli stessi file di `regole/`.

## Gradino 1 — chat semplice, nessun documento

> Nel collaudo di macchine automatiche si usano di norma le fasi FAT e SAT descritte dalla IEC 62381, con esito espresso come *passed / passed with deviations / failed* e una punch list allegata. La scheda riporta di solito identificativo della prova, criterio di accettazione, esito e firma delle parti.

È la risposta più fluente delle tre, ed è quella sbagliata. È l'impianto normativo del settore, e non è sbagliato in generale. Semplicemente non è il vostro: la casa usa una scala interna a cinque livelli che nessun modello può conoscere, e i campi obbligatori sono undici, non quattro.

## Gradini 2 e 3 — con i documenti della casa

La scala interna, dal documento:

- **CE-1 — Collaudo chiuso**: Tutte le prove superate e tempo ciclo entro contratto.
- **CE-2 — Chiuso con riserva**: Almeno il 90% delle prove superate, scostamenti annotati.
- **CE-3 — Parziale**: Almeno l'80% delle prove superate: consegna condizionata.
- **CE-4 — Incompleto**: Fra il 65% e l'80% delle prove: nuova sessione necessaria.
- **CE-5 — Non concluso**: Meno del 65% delle prove eseguite: collaudo da rifare.

I campi obbligatori, dal documento — sono 11:

1. riferimento collaudo interno (formato CLD-<anno>-<numero>)
2. tipo di collaudo: in fabbrica (FAT) o in sito (SAT)
3. commessa e macchina
4. riferimento e revisione della specifica di prova
5. versione del software consegnata al collaudo
6. codice articolo del PLC, oppure la dicitura NON DETERMINATO
7. riferimento e versione del blocco di libreria usato
8. prove eseguite sul totale, prove non superate e punti aperti con la loro categoria
9. tempo ciclo misurato e tempo ciclo a contratto
10. classe di esito della scala interna CE-1 / CE-5
11. firma del tecnico e firma del cliente, oppure la dicitura FIRMA CLIENTE ASSENTE

**Passaggio recuperato:** `regole/standard-collaudo.md`, sezioni 1 e 2 — più `regole/guida-scala-esito.md` per la regola del dubbio fra due livelli adiacenti.

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

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

> Il rendimento di un impianto fotovoltaico si esprime con il performance ratio definito dalla IEC 61724-1, di norma con soglie indicative attorno all'80 % per impianti in buono stato, e la scheda riporta produzione, irraggiamento, ore equivalenti e fermi.

È la risposta più fluente delle tre, ed è quella sbagliata. È la definizione di riferimento del settore, e non è sbagliata in generale. Semplicemente non è la vostra: la casa usa una scala interna a cinque livelli con soglie proprie, e la pratica sammarinese non è quella italiana.

## Gradini 2 e 3 — con i documenti della casa

La scala interna, dal documento:

- **RG-1 — Eccellente**: Performance ratio pari o superiore all'87%: impianto al di sopra dell'atteso.
- **RG-2 — Buono**: Performance ratio fra 80% e 87%: nessun intervento necessario.
- **RG-3 — Regolare**: Performance ratio fra 73% e 80%: da tenere sotto osservazione.
- **RG-4 — Sotto soglia**: Performance ratio fra 66% e 73%: sopralluogo da programmare.
- **RG-5 — Fuori specifica**: Performance ratio inferiore al 66%: intervento entro il mese.

I campi obbligatori, dal documento — sono 8:

1. riferimento impianto interno (formato RSM-<anno>-<numero>)
2. potenza in kWp con una cifra decimale, e presenza o assenza di accumulo
3. matricola del contatore di scambio
4. irraggiamento del mese sul piano dei moduli in kWh/m2
5. energia prodotta nel mese in kWh, energia immessa in rete e ore equivalenti
6. performance ratio misurato, con una cifra decimale
7. classe di rendimento della scala interna RG-1 / RG-5
8. numero di pratica dell'Ufficio Energia, oppure la dicitura NON DETERMINATO

**Passaggio recuperato:** `regole/istruzione-monitoraggio.md`, sezioni 1 e 2 — più `regole/guida-scala-rendimento.md` per la regola del dubbio fra due livelli adiacenti.

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

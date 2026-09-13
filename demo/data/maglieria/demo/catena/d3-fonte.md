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

> Le richieste di modifica a un gestionale si classificano di norma con MoSCoW — Must, Should, Could, Won't — oppure con una matrice priorità/gravità, e si dimensionano in punti storia; i criteri di accettazione si scrivono in forma Given/When/Then e la scheda riporta descrizione, priorità, stima, criteri di accettazione e definition of done.

È la risposta più fluente delle tre, ed è quella sbagliata. È la pratica corrente della gestione requisiti, ed è corretta in generale. Semplicemente non è la vostra, e per una ragione precisa: MoSCoW e i punti storia misurano <b>priorità e dimensione</b>, mentre la scala SP misura quanta specifica manca ancora alla richiesta e chi deve firmarla. Nessun quadro di priorità ha un livello che dice «questo non deve diventare un ticket perché non è un problema di software»: il vostro SP-5 sì. E i campi obbligatori della casa sono undici, non cinque.

## Gradini 2 e 3 — con i documenti della casa

La scala interna, dal documento:

- **SP-1 — Specifica diretta**: L'intervento resta nel software, non tocca il modello dati e i dati di processo del reparto sono stati rilevati: la specifica si chiude con la firma del solo revisore ed entra in stima.
- **SP-2 — Specifica assistita**: L'intervento resta nel software e i dati di processo sono rilevati, ma introduce un nuovo campo: prima della stima serve una conferma con il committente sul significato del campo e su chi lo compila.
- **SP-3 — Specifica da rilevare**: I dati di processo sono dichiarati dal committente oppure non disponibili: la specifica non si chiude finché non è stata fatta la rilevazione in reparto, e la stima resta NON STIMABILE.
- **SP-4 — Specifica sospesa**: L'intervento modifica record già in produzione: servono l'approvazione scritta del committente e la firma di un secondo revisore prima che la specifica entri in sviluppo.
- **SP-5 — Fuori specifica**: La richiesta cambia il processo del committente e non il software: non diventa un ticket e torna al committente come proposta di intervento sul processo, mai come stima.

I campi obbligatori, dal documento — sono 11:

1. riferimento interno di specifica (formato SPEC-<anno>-<numero>)
2. codice cliente (formato CLI-<numero>) e tipo di committente, senza il nome dell'azienda
3. modulo del gestionale interessato e versione in esercizio, nel formato vX.Y
4. canale di arrivo della richiesta e data
5. reparto e fase del committente toccati dall'intervento
6. stato dei dati di processo — rilevati, dichiarati o non disponibili — con il riferimento della rilevazione, oppure la dicitura RILEVAZIONE NON ESEGUITA
7. tempo standard della fase in minuti a capo se rilevato, altrimenti la dicitura NON RILEVATO
8. criteri di accettazione misurabili, almeno due, oppure la dicitura NON DEFINITI
9. impatto sul modello dati: nessuno, nuovo campo, oppure modifica di record già in produzione
10. stima in giornate-uomo con l'intervallo minimo-massimo, oppure la dicitura NON STIMABILE
11. classe di specifica della scala interna SP-1 / SP-5, e per SP-4 e SP-5 l'approvazione scritta del committente oppure la dicitura APPROVAZIONE CLIENTE ASSENTE

**Passaggio recuperato:** `regole/standard-specifica.md`, sezioni 1 e 2 — più `regole/guida-scala-specifica.md` per la regola del dubbio fra due livelli adiacenti.

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

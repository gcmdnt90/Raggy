# Servizio Specifiche e Sviluppo Gestionale — Standard interno di specifica e accettazione

*Edizione in vigore per le richieste dei committenti. San Marino.*

## 1. Scala interna di specifica

La casa adotta una scala interna a cinque livelli, denominata **scala SP**, assegnata a ogni richiesta prima che entri in stima. La scala non misura né la priorità né la dimensione del lavoro: misura **quanta specifica manca ancora alla richiesta e chi deve firmarla**. Non equivale a MoSCoW, ai punti storia né ad alcuna matrice priorità/gravità, e ogni conversione richiede il parere del revisore che firma la specifica.

- **SP-1 — Specifica diretta**: L'intervento resta nel software, non tocca il modello dati e i dati di processo del reparto sono stati rilevati: la specifica si chiude con la firma del solo revisore ed entra in stima.
- **SP-2 — Specifica assistita**: L'intervento resta nel software e i dati di processo sono rilevati, ma introduce un nuovo campo: prima della stima serve una conferma con il committente sul significato del campo e su chi lo compila.
- **SP-3 — Specifica da rilevare**: I dati di processo sono dichiarati dal committente oppure non disponibili: la specifica non si chiude finché non è stata fatta la rilevazione in reparto, e la stima resta NON STIMABILE.
- **SP-4 — Specifica sospesa**: L'intervento modifica record già in produzione: servono l'approvazione scritta del committente e la firma di un secondo revisore prima che la specifica entri in sviluppo.
- **SP-5 — Fuori specifica**: La richiesta cambia il processo del committente e non il software: non diventa un ticket e torna al committente come proposta di intervento sul processo, mai come stima.

## 2. Campi obbligatori in ogni scheda di specifica

Nessuna scheda può essere chiusa se manca anche uno solo dei campi seguenti:

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

## 3. Regole di redazione

- 3.1 Il nome del maglificio committente non compare mai in una scheda di specifica: si usano il codice cliente e il tipo di committente. Una scheda che riporta il nome non esce dall'ufficio.
- 3.2 Nessuna scheda riporta tempi di fase, rese o cali che non siano stati rilevati in reparto: un dato riferito dal committente si scrive sempre «dichiarato, non rilevato», con la data in cui è stato riferito.
- 3.3 Una richiesta senza almeno due criteri di accettazione misurabili non entra in stima: si scrive NON DEFINITI, la stima è NON STIMABILE e la richiesta torna al committente.
- 3.4 Nessuna scheda può contenere una percentuale di miglioramento, di resa o di riduzione dei tempi: è una proiezione commerciale e non un requisito.
- 3.5 Una richiesta che modifica record già in produzione è almeno SP-4: servono l'approvazione scritta del committente e la firma di un secondo revisore prima dello sviluppo.
- 3.6 Una richiesta che cambia il processo del committente e non il software è SP-5: non diventa un ticket e torna come proposta di intervento sul processo, mai come stima.

## 4. Responsabilità

La responsabilità finale della specifica resta in capo al revisore che la firma. Strumenti automatici possono produrre bozze, mai schede chiuse: un modulo, una versione in esercizio, un tempo di fase o un codice cliente prodotti da un assistente valgono come proposta, non come dato.

---

_Documento sintetico generato per formazione — non usare in produzione._

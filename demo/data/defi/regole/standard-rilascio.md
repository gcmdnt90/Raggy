# Servizio Revisione e Rilascio Contratti — Standard interno di revisione e rilascio

*Edizione in vigore per i rilasci in rete principale. San Marino.*

## 1. Scala interna di rischio di rilascio

La casa adotta una scala interna a cinque livelli, denominata **scala RD**, assegnata a ogni rilascio prima della messa in rete. La scala non equivale ad alcuna classificazione di gravità usata dalle società di revisione: combina rilievi aperti, copertura dei test e finestra di timelock, e ogni conversione richiede il parere del revisore che firma il rilascio.

- **RD-1 — Rilascio diretto**: Nessun rilievo critico o alto aperto, copertura dei test pari o superiore all'85% e timelock di almeno 48 ore: il rilascio procede con la firma di un solo revisore.
- **RD-2 — Rilascio sorvegliato**: Nessun rilievo critico, al più un rilievo alto già chiuso o tre rilievi medi: il rilascio procede con monitoraggio giornaliero per sette giorni.
- **RD-3 — Rilascio limitato**: Nessun rilievo critico aperto ma timelock inferiore a 48 ore oppure copertura dei test sotto l'85%: si rilascia con esposizione massima ridotta e monitoraggio per quattordici giorni.
- **RD-4 — Rilascio sospeso**: Almeno un rilievo alto aperto, oppure copertura dei test sotto il 70%: serve la firma di un secondo revisore e la richiusura del rilievo prima della messa in rete.
- **RD-5 — Non rilasciabile**: Rilievo critico aperto, oppure commit di rilascio non tracciato: la scheda non può essere chiusa e il rilascio non entra in rete principale.

## 2. Campi obbligatori in ogni scheda di rilascio

Nessuna scheda può essere chiusa se manca anche uno solo dei campi seguenti:

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

## 3. Regole di redazione

- 3.1 Nessuna scheda può riportare un rendimento atteso, storico o garantito: sono proiezioni commerciali, non dati di rilascio.
- 3.2 Un indirizzo di contratto non verificato sull'explorer va sempre accompagnato dalla dicitura DA VERIFICARE. Un indirizzo prodotto da un assistente e non verificato non entra in nessun documento che esce dalla casa.
- 3.3 Un rilascio in classe RD-4 o RD-5 non può andare in rete principale senza timelock di almeno 48 ore e la firma di due revisori.
- 3.4 Il riferimento a una revisione esterna può comparire solo se il report è pubblicato: finché non lo è si scrive NON DETERMINATO.
- 3.5 Nessuna dichiarazione di conformità normativa, di assenza di rischio o di avvenuto audit può essere inserita da chi redige la scheda.
- 3.6 Ogni scheda riporta il commit di rilascio e la rete di destinazione: una versione senza commit non è rilasciabile.

## 4. Responsabilità

La responsabilità finale del rilascio resta in capo al revisore che lo firma. Strumenti automatici possono produrre bozze, mai schede chiuse: un indirizzo, un commit o un riferimento di revisione prodotti da un assistente valgono come proposta, non come dato.

---

_Documento sintetico generato per formazione — non usare in produzione._

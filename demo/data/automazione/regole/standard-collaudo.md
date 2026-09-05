# Software House Automazione — Standard interno di programmazione e collaudo

*Edizione in vigore per le commesse in collaudo. San Marino.*

## 1. Scala interna di esito collaudo

L'azienda adotta una scala interna a cinque livelli, denominata **scala CE**, assegnata a ogni collaudo prima della consegna. La scala non equivale ad alcuna classificazione normativa: ogni conversione richiede il parere del tecnico che firma il collaudo.

- **CE-1 — Collaudo chiuso**: Tutte le prove superate e tempo ciclo entro contratto.
- **CE-2 — Chiuso con riserva**: Almeno il 90% delle prove superate, scostamenti annotati.
- **CE-3 — Parziale**: Almeno l'80% delle prove superate: consegna condizionata.
- **CE-4 — Incompleto**: Fra il 65% e l'80% delle prove: nuova sessione necessaria.
- **CE-5 — Non concluso**: Meno del 65% delle prove eseguite: collaudo da rifare.

## 2. Campi obbligatori in ogni scheda di collaudo

Nessuna scheda può essere consegnata al cliente se manca anche uno solo dei campi seguenti:

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

## 3. Regole di redazione

- 3.1 Nessuna logica e nessuna dichiarazione sulle funzioni di sicurezza (livelli PL/SIL) può essere redatta da chi compila la scheda.
- 3.2 Nessuna dichiarazione di conformità CE può comparire in un verbale di collaudo.
- 3.3 Un collaudo che si chiude con esito parziale, cioè in classe CE-3, si consegna solo con la lista dei punti aperti allegata, ognuno con la sua categoria, e con la data della sessione di recupero già fissata.
- 3.4 Un esito non confermato dal tecnico va sempre accompagnato dalla dicitura DA VERIFICARE.
- 3.5 I collaudi in classe CE-5 non possono essere consegnati al cliente.
- 3.6 Un verbale privo della firma del cliente resta interno e non fa fede come accettazione.
- 3.7 Ogni scheda riporta il nome dell'operatore che l'ha redatta e la data della sessione.

## 4. Responsabilità

La responsabilità finale dell'esito resta in capo al tecnico che firma il collaudo. Strumenti automatici possono produrre bozze, mai esiti validati.

---

_Documento sintetico generato per formazione — non usare in produzione._

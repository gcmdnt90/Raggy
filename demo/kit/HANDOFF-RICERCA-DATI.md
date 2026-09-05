---
title: Brief di sessione — ricerca dati per rendere verosimili i dati sintetici delle demo
scope: delivery/demo-data-kit (tre settori) + delivery/theory-deck/demo-prompts.json
written: 2026-09-01
---

# Ricerca: che forma hanno davvero questi documenti

> **Svolto il 02/09/2026.** Il rapporto è in `RICERCA-DATI.md`, le correzioni
> sono applicate alle tre config e ai moduli di settore, i dati rigenerati.
> Resta aperto solo il **punto D** (una fotografia con licenza per settore).
> Questo brief si tiene come traccia di che cosa era stato chiesto.

## Che cosa stiamo costruendo

`delivery/theory-deck` è una lezione di due ore su LLM e agenti per PMI, in
cinque moduli, ognuno dei quali si chiude con una demo dal vivo. Una sola
scelta di **settore**, fatta sulla slide della scaletta prima di iniziare,
pilota tutti i widget e tutte le demo. I settori sono tre:

| id | settore | documento di lavoro |
|---|---|---|
| `numismatica` | casa d'aste numismatica | scheda di lotto |
| `fotovoltaico` | monitoraggio e ottimizzazione impianti FV | scheda di rendimento mensile |
| `automazione` | software house per l'automazione industriale | scheda di protocollo di collaudo |

`delivery/demo-data-kit` genera i documenti sintetici su cui girano le demo:
un modulo Python per settore sopra una spina dorsale condivisa, una config
JSON per settore, seed deterministico. Uscita in `delivery/demo-data/<settore>/`.

## L'obiettivo di questa sessione, detto con precisione

**Non** si cercano i dati veri dei clienti, e non serve che i nostri dati
coincidano con i loro. Serve che i nostri documenti sintetici abbiano la
**forma giusta**: i campi che quel mestiere usa davvero, nell'ordine in cui li
scrive, con le unità di misura e i formati di codice che usa, e con **gli
errori tipici che quei documenti contengono davvero** — campi lasciati vuoti,
valori dichiarati e non misurati, sigle non annotate, note scritte di corsa.

Il motivo è operativo: in aula c'è sempre una persona che quel documento lo
compila tutti i giorni. Se la forma è sbagliata, se ne accorge in tre secondi e
la lezione perde credibilità. Se la forma è giusta, il fatto che i valori siano
inventati non disturba nessuno — anzi, è quello che diciamo esplicitamente.

Se poi in aula vogliono cambiare dati o prompt, si fa a mano lì per lì: il kit
è rigenerabile e i prompt sono in un solo file. Questa ricerca serve a partire
da una base credibile, non a indovinare il caso specifico.

## Vincoli invalicabili

1. **La scala interna deve restare inventata.** Ogni settore ha una scala a
   cinque livelli — SM-1…SM-5 (conservazione), RG-1…RG-5 (rendimento mensile),
   CE-1…CE-5 (esito collaudo). Sono inventate **apposta**: il modulo 3 mette a
   confronto un modello senza documenti e uno con i documenti dell'azienda, e
   il confronto si legge solo perché la scala non è indovinabile. Se la
   ricerca trova una scala reale e standard, quella va **documentata nelle
   note** come termine di paragone, non messa nei documenti generati.
   Sostituire la scala inventata con una reale distrugge la demo.
2. **Ogni affermazione con la sua fonte.** Link, titolo, ente, data di
   consultazione. Se una cosa non si trova in una fonte affidabile, si scrive
   che non si è trovata — non si riempie il buco a intuito.
3. **Solo materiale liberamente e legalmente disponibile.** Va verificata e
   riportata la licenza di ogni dataset, immagine o documento. Niente scraping
   di cataloghi d'asta commerciali, niente materiale sotto copyright ripubblicato.
   Preferire dati pubblici di enti (musei, laboratori nazionali, portali open data)
   e licenze esplicite (CC0, CC BY, ODbL, pubblico dominio).
4. **Niente dati di clienti reali**, né di Artemide né di nessun altro.
5. **Il kit deve continuare a girare.** Ogni proposta di modifica va espressa
   come modifica alla config di settore o al modulo di settore, e verificata
   lanciando `python generate.py --settore <id>`.

## Che cosa serve, settore per settore

Per ciascun settore, rispondere a queste domande con fonti:

### A. Struttura del documento
- Quali campi contiene davvero il documento di lavoro di quel mestiere, e in
  che ordine compaiono?
- Quali sono obbligatori per prassi o per norma, e quali facoltativi?
- Che formato hanno i codici identificativi (riferimento interno, codice
  pratica, codice articolo)? Che aspetto ha un codice vero?
- Quali unità di misura, con quante cifre decimali?

### B. Errori e imprecisioni tipiche
- Quali campi restano vuoti più spesso, nella pratica?
- Quali valori vengono dichiarati e non misurati?
- Dove nascono le ambiguità che poi qualcuno deve verificare a mano?
  Questo è il materiale che fa funzionare le battute 1 e 3 della demo di M4:
  senza regole il modello riempie il buco, con le regole lo lascia vuoto e lo
  contrassegna.

### C. Vocabolario
- Come si chiamano le cose in italiano, nel gergo di quel mestiere?
  I documenti generati sono in italiano e devono suonare interni, non tradotti.

### D. Una fotografia per settore, con licenza
La demo di M5 mostra un'attribuzione a freddo su una foto (`m5-p2`, `m5-p3`).
Oggi esiste solo il caso numismatico e manca la foto per gli altri due. Serve
**un'immagine per settore**, liberamente utilizzabile e con licenza dichiarata:
una moneta antica, un modulo fotovoltaico con la targhetta leggibile, un
componente di automazione con la sua targhetta. Salvarle in
`delivery/theory-deck/assets/img/` e registrare fonte e licenza.

## Stato attuale, da validare o correggere

Questi sono i valori **inventati da noi** oggi. Vanno confrontati con la
realtà documentata e corretti dove la forma è sbagliata.

### `config/numismatica.json`
- Riferimento di catalogo `ART-<anno>-<numero>`, peso in grammi con una
  decimale, diametro in mm, autorità emittente e periodo, provenienza.
- Campi di giudizio inventati per il modulo 2: rarità `R1…R5`, domanda attesa
  bassa/media/alta.
- *Da verificare:* come descrive davvero un lotto una casa d'aste numismatica;
  se esistono convenzioni di rarità diffuse (e quali) e come vengono scritte;
  quali informazioni di provenienza sono obbligatorie e quali si omettono.

### `config/fotovoltaico.json`
- Riferimento impianto `RSM-<anno>-<numero>`, potenza in kWp, accumulo in kWh,
  energia prodotta in kWh, ore equivalenti, **performance ratio in percentuale**,
  codice pratica incentivo, allarmi inverter.
- Campi di giudizio inventati: perdita di produzione in kWh, urgenza del
  cliente, distanza in km.
- *Da verificare:* che cosa contiene davvero un report di rendimento mensile di
  un servizio di monitoraggio; come si calcola e si dichiara il performance
  ratio (esiste una norma di riferimento — verificare **IEC 61724-1** e che cosa
  prescrive); che aspetto ha un codice pratica di incentivo; quali sono gli
  allarmi ricorrenti e come si chiamano.

### `config/automazione.json`
- Riferimento collaudo `CLD-<anno>-<numero>`, commessa, macchina, codice
  articolo PLC, blocco di libreria con versione, prove eseguite su totale,
  tempo ciclo misurato contro tempo ciclo a contratto.
- Campi di giudizio inventati: fermo linea del cliente in ore, prove ancora
  aperte, trasferta in km.
- *Da verificare:* la struttura reale di un protocollo di collaudo (FAT/SAT) —
  verificare **IEC 62381** (Automation systems in the process industry:
  factory/site acceptance tests) e **IEC 62337** (commissioning); che aspetto
  hanno i codici articolo PLC dei costruttori diffusi; come si nominano i
  blocchi di libreria e le loro versioni.

## Piste di partenza già verificate come esistenti

Esistono, la licenza va comunque controllata e riportata.

**Numismatica**
- [Online Coins of the Roman Empire (OCRE)](https://numismatics.org/ocre/) —
  American Numismatic Society + ISAW/NYU. Ha una
  [API documentata](https://numismatics.org/ocre/apis?lang=en).
- [nomisma.org — Datasets](http://nomisma.org/datasets) — vocabolari e dataset
  linked-data del dominio numismatico.
- [ANS — Online resources](https://numismatics.org/online-resources-working/).
- Da valutare anche le collezioni museali con API aperta e immagini in licenza
  libera, utili per il punto D.

**Fotovoltaico**
- [PVDAQ Public Datasets — NREL / OEDI](https://data.openei.org/submissions/4568),
  anche su [data.gov](https://catalog.data.gov/dataset/photovoltaic-data-acquisition-pvdaq-public-datasets)
  e con [documentazione su GitHub](https://github.com/openEDI/documentation/blob/main/pvdaq.md).
- [Open data sets for assessing photovoltaic system reliability](https://www.sciencedirect.com/science/article/pii/S0306261925008621)
  — rassegna, utile come indice di dataset.
- Da cercare: PVGIS (JRC, Commissione europea) per irraggiamento e resa attesa;
  portali di monitoraggio con dati pubblici.

**Automazione**
- [IEC 62381:2024](https://webstore.iec.ch/en/publication/67572) — norma a
  pagamento, ma l'indice è leggibile nell'
  [anteprima ANSI della ed. 2.0](https://webstore.ansi.org/preview-pages/iec/preview_iec62381%7Bed2.0%7Db.pdf),
  e l'indice è quasi tutto quello che ci serve: dice quali sezioni ha un
  protocollo di collaudo.
- [IEC 62337 — Commissioning](https://standards.globalspec.com/std/1564624/IEC%2062337).
- [Systematic Approach to Factory Acceptance Test Planning](https://www.researchgate.net/publication/263406060_Systematic_Approach_to_Factory_Acceptance_Test_Planning) — paper.
- Template pubblici di FAT ([SafetyCulture](https://safetyculture.com/library/manufacturing/factory-acceptance-template),
  [Operations1](https://operations1.com/en/resources/factory-acceptance-test-template)):
  utili come indizio sulla forma, **non** citabili come fonte autorevole e da
  non copiare — verificarne i termini d'uso prima di ispirarvisi.

## Dove sono i file

```
delivery/demo-data-kit/
  README.md                      come funziona il kit, come si aggiunge un settore
  generate.py                    CLI: --settore --nome --out --seed
  config/{numismatica,fotovoltaico,automazione}.json
  generators/settori/            un modulo per settore + il contratto in __init__.py
delivery/demo-data/<settore>/    uscita generata (regole/, schede/, avvelenata/, demo/, _perito/)
delivery/theory-deck/demo-prompts.json    i prompt di tutte le demo, con le varianti per settore
delivery/DEMO-CHECKLIST.md       la scaletta operativa delle demo
```

Leggere `delivery/demo-data-kit/README.md` prima di toccare qualsiasi cosa: la
sezione «Adding a sector» descrive il contratto che ogni modulo di settore deve
rispettare, e la sezione su `demo/` spiega perché tutti i moduli devono parlare
degli stessi record.

## Che cosa consegnare

1. **`delivery/demo-data-kit/RICERCA-DATI.md`** — il rapporto. Per ogni
   settore: struttura reale del documento, errori tipici, vocabolario, con le
   fonti in fondo a ogni sezione. Dove la ricerca non ha trovato niente di
   affidabile, dirlo esplicitamente invece di riempire.
2. **Le modifiche alle tre config**, applicate e verificate rilanciando
   `python generate.py --settore <id>` per tutti e tre. Non cambiare la
   struttura dei moduli di settore se non è necessario; se serve, rispettare il
   contratto in `generators/settori/__init__.py`.
3. **Le tre fotografie** del punto D, con un file di provenienza che riporti
   per ciascuna: URL, autore, ente, licenza, data di consultazione.
4. **Una riga per ogni prompt di `demo-prompts.json` che va corretto** perché
   la ricerca ha mostrato che chiede una cosa che quel mestiere non chiama così.
   Non modificarli senza segnalarlo: i prompt sono stati rivisti uno a uno.

## Criteri di accettazione

- Un professionista di quel settore, guardando un documento generato, non trova
  niente di strutturalmente sbagliato — anche sapendo che i valori sono finti.
- Le scale interne SM / RG / CE restano inventate e la scala del modulo 3
  continua a funzionare: un modello senza documenti non può indovinarle.
- Tutti e tre i settori generano senza errori e la cartella `demo/` continua a
  produrre i ritagli per M1, M2 e M4.
- Ogni affermazione nel rapporto ha una fonte, e ogni immagine una licenza.

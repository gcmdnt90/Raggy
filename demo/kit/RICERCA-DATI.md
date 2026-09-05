---
title: Ricerca — che forma hanno davvero i documenti dei tre settori
scope: delivery/demo-data-kit (config + moduli di settore) e delivery/demo-data
answers: HANDOFF-RICERCA-DATI.md
date: 2026-09-02
---

# Che forma hanno davvero questi documenti

Rapporto della sessione di ricerca chiesta da `HANDOFF-RICERCA-DATI.md`.
Per ogni settore: che cosa contiene davvero il documento di lavoro, quali
errori contiene tipicamente, come si chiamano le cose in italiano, che cosa è
stato corretto nel kit e che cosa **non** si è trovato.

Regola applicata dappertutto: **si è corretta la forma, non i valori.** I
valori restano inventati e dichiarati tali in `LEGGIMI-SINTETICO.md`. Le tre
scale interne — SM, RG, CE — restano inventate: sono il perno del modulo 3 e
sostituirle con una scala reale distruggerebbe la demo.

---

## 1. Numismatica — la scheda di lotto

### Struttura reale

Il riferimento normativo italiano è la **scheda NU dell'ICCD** (Ministero della
Cultura), versione 3.00: è catalogazione museale, non una scheda d'asta, ma
fissa i campi e il lessico che tutto il mestiere usa. I paragrafi rilevanti e
i loro codici: `OGTO` nominale, `AUEE` autorità emittente, `ZEC` zecca,
`MTC` materia e tecnica, `MISG` peso, `MISD` diametro, **`MTA` andamento
conii** (l'asse), `STCC` stato di conservazione e `STCL` leggibilità, `DTZG`
fascia cronologica, `BIB` bibliografia con `BIBH` sigla, `ACQT`/`ACQD` tipo e
data di acquisizione.

Le schede d'asta e i cataloghi online seguono lo stesso ordine, con l'aggiunta
dei campi commerciali: nominale → metallo → peso → diametro → asse di conio →
zecca → autorità e datazione → descrizione di dritto, rovescio e legenda →
**riferimento bibliografico** (sigla e numero) → conservazione → rarità →
provenienza → stima e base d'asta.

Tre convenzioni verificate, e non negoziabili se la scheda deve reggere:

- **Asse di conio**, scritto in ore (`ore 6`, `ore 12`). È il campo più
  caratteristico della monetazione antica e mancava del tutto.
- **Riferimento bibliografico**: sigla dell'opera di riferimento più numero —
  `RIC V 202`, `Crawford 44/5`, `CNI XIII 145`, `Muntoni 112`, `Paolucci 79`.
  È l'ancora dell'attribuzione: senza, l'attribuzione è un'opinione.
- **Rarità**: la convenzione corrente è `C` (comune), `NC` (non comune), `R`,
  `R2`, `R3`. **`R1` non esiste**: nessuno lo scrive.

### Errori e imprecisioni tipiche

- L'asse di conio è il primo campo che salta su una bozza scritta di corsa.
- Il riferimento bibliografico resta aperto finché il perito non conferma
  l'attribuzione; zecca e periodo lo seguono.
- Il peso da bilancia da banco viene riportato e poi ricontrollato.
- La provenienza è spesso parziale o assente: la dicitura esplicita
  «provenienza non documentata» è pratica corrente, non una svista.

### Vocabolario

Nominale, dritto (D/), rovescio (R/), legenda, campo, esergo, contorno, conio,
asse di conio, zecca, patina, decentratura, tosatura, esemplare, lotto,
invenduto, perito, diritti d'asta.

### Che cosa è stato corretto

| Prima | Adesso | Perché |
|---|---|---|
| nessun asse di conio | `Asse di conio: ore 6` | campo obbligatorio nella pratica reale |
| «Riferimento di catalogo: ART-2026-003» come unico riferimento | `Riferimento interno di lotto` **più** `Riferimento bibliografico` | erano due cose diverse chiamate con lo stesso nome |
| nessuna zecca | `Zecca`, coerente con il tipo | ICCD `ZEC`; ogni scheda ce l'ha |
| rarità `R1…R5` | `C / NC / R / R2 / R3` | `R1` non è una sigla in uso |
| peso a una decimale | due decimali | i cataloghi pesano al centesimo di grammo |
| iconografia e legende da un unico elenco | pool per epoca (repubblicana, imperiale, tardoimperiale, medievale) | un antoniniano di Gallieno con la Roma elmata repubblicana è l'errore che il perito vede in tre secondi |
| lotto avvelenato: Grosso di bronzo da 9,4 g | tipo preso dalla config, peso e diametro dal suo intervallo | la scheda avvelenata deve reggere lo stesso esame delle altre |

### Deviazione consapevole

Una scheda d'asta vera porta il grado di mercato italiano — **FDC, SPL, BB,
MB, B, D**, con i modificatori `q.` (quasi) e `+`, e la notazione `MB/BB`
quando dritto e rovescio differiscono. Le nostre schede portano **solo** la
scala SM inventata. È voluto: la scala SM è ciò che un modello non può
indovinare, ed è quello che rende leggibile il confronto fra i gradini del
modulo 3. Se in aula qualcuno lo nota, la risposta è già nel regolamento
generato: «la scala non è convertibile automaticamente in altre scale di
mercato».

### Fonti

- ICCD, *Scheda NU — Beni numismatici, versione 3.00*, norme di compilazione —
  <https://iccd.cultura.gov.it/it/ricercanormative/18/nu-beni-numismatici-3_00>
  (consultato 02/09/2026)
- Wikipedia IT, *Conservazione (numismatica)* — scala FDC/SPL/BB/MB/B/D e
  modificatori — <https://it.wikipedia.org/wiki/Conservazione_(numismatica)>
  (CC BY-SA, consultato 02/09/2026)
- Numispedia, scheda di catalogo di esempio (ordine dei campi: nominale,
  materiale, diametro, peso, asse di conio, zecca, bibliografia, rarità) —
  <https://numispedia.it/catalog/coin/2396> (consultato 02/09/2026)
- Online Coins of the Roman Empire (ANS/ISAW) — <https://numismatics.org/ocre/>
  e nomisma.org — <http://nomisma.org/datasets> (vocabolari linked-data;
  **non usati** per generare dati, registrati come pista aperta)

---

## 2. Fotovoltaico — la scheda di rendimento mensile

### Struttura reale

Il riferimento è la **IEC 61724-1** (*Photovoltaic system performance — Part 1:
Monitoring*). Definisce il performance ratio come rapporto fra resa specifica
misurata e resa di riferimento:

    PR = Yf / Yr = (E [kWh] / P [kWp]) / (H_POA [kWh/m2] / 1 kW/m2)

Cioè: **PR = ore equivalenti ÷ irraggiamento sul piano dei moduli.** Questa è
la correzione più importante di tutta la ricerca.

Un report mensile di monitoraggio contiene, nell'ordine: identificazione
dell'impianto (riferimento, sito, potenza in kWp, accumulo, inverter,
esposizione e inclinazione, matricola del contatore) → dati del mese
(irraggiamento, energia prodotta, energia immessa in rete, energia prelevata,
autoconsumo, ore equivalenti, performance ratio, disponibilità) → allarmi e
giorni di fermo → note e firma del tecnico.

### Errori e imprecisioni tipiche

- **L'autoconsumo è quasi sempre stimato, non misurato**, quando c'è solo il
  contatore di scambio. È la fonte di ambiguità numero uno.
- La lettura del contatore e il dato del datalogger non coincidono: si sceglie
  quale fa fede e lo si dichiara.
- I giorni di fermo non finiscono sul registro, e la produzione persa viene
  ricostruita a posteriori.
- La pratica di incentivo è la voce che resta «da recuperare» più a lungo.

### Vocabolario

Irraggiamento sul piano dei moduli, ore equivalenti (o ore di funzionamento
equivalenti), performance ratio, resa specifica, energia immessa e prelevata,
autoconsumo, contatore di scambio e contatore di produzione, punto di consegna,
stringa, derating, ombreggiamento, datalogger, sopralluogo.

### Che cosa è stato corretto

| Prima | Adesso | Perché |
|---|---|---|
| PR estratto a caso, indipendente da produzione e ore equivalenti | catena aritmetica: irraggiamento → PR → ore equivalenti → kWh | dodici impianti nello stesso agosto con irraggiamento implicito da 93 a 250 kWh/m2 non possono essere tutti veri |
| nessun irraggiamento in scheda | `Irraggiamento sul piano dei moduli: 165,3 kWh/m2` | senza, il PR non è verificabile: è la definizione IEC 61724-1 |
| solo energia prodotta | anche `Energia immessa in rete` | il contatore di scambio misura quella, non la produzione |
| nessun inverter, esposizione, matricola | tre campi in testa alla scheda | ci sono su qualunque report reale |
| «Riferimento decreto e codice pratica: PR-2026-452» | `Pratica Ufficio Energia: UE-2026-452` | `PR` collideva con performance ratio; l'interlocutore sammarinese è l'Ufficio Energia |
| nessun giorno di fermo | `Giorni di fermo`, coerente con l'allarme | una nota del kit già ci si riferiva |

Tutte e dodici le schede sono state riverificate: `PR × irraggiamento = ore
equivalenti` e `ore equivalenti × kWp = kWh` tornano su ogni riga, e
l'irraggiamento del mese sta fra 159 e 182 kWh/m2 su tutto il parco.

### Materiale per la verifica in M4

Nei dati grezzi di M4 il cliente dichiara «autoconsumo circa il 60%», mentre
l'energia immessa in rete dice un'altra cosa. La contraddizione è voluta: è
esattamente ciò che la regola 3.5 del regolamento generato obbliga a segnalare.

### Che cosa non si è trovato

- **Il regime di incentivo sammarinese in vigore nel 2026.** Il Decreto
  Delegato 25 giugno 2009 n. 92 istituisce la tariffa incentivante e la
  procedura con l'Ufficio Energia, ma non si è trovata conferma di quale
  provvedimento sia oggi applicabile. Per questo la scheda cita un **numero di
  pratica**, non un decreto: dire «pratica Ufficio Energia UE-2026-452» è vero
  come forma senza affermare nulla di falso sul merito.
- Il formato reale di un codice pratica dell'Ufficio Energia. Quello usato è
  inventato e coerente, nulla di più.
- Non si è usato il **POD** italiano (`IT001E…`): è la convenzione del
  distributore italiano, e a San Marino il distributore è l'AASS. La matricola
  del contatore è neutra e vera dappertutto.

### Fonti

- IEC 61724-1:2017, *Photovoltaic system performance — Part 1: Monitoring*
  (norma a pagamento) — <https://webstore.ansi.org/standards/iec/iec61724eden2017>
- SevenSensor, *How to calculate PR using POA irradiance data according to
  IEC 61724-1* — formula e variabili —
  <https://www.sevensensor.com/how-to-calculate-pr-performance-ratio-using-poa-irradiance-data-according-to-iec-61724-1>
  (consultato 02/09/2026)
- AASS, *Decreto Delegato 25 giugno 2009 n. 92* — tariffa incentivante,
  Ufficio Energia, contatori, punto di consegna —
  <https://www.aass.sm/site/home/elettricita/energie-rinnovabili/documento50001174.html>
  (consultato 02/09/2026)
- Element Energia, esempio pubblico di report di monitoraggio (voci: prodotta,
  consumata, autoconsumata, immessa, prelevata) —
  <https://www.elementenergia.com/2020/04/monitoraggio-fotovoltaico-ecco-uno-dei-nostri-report/>
  (consultato 02/09/2026)
- PVDAQ Public Datasets, NREL/OEDI — <https://data.openei.org/submissions/4568>
  (pista aperta: dati reali per calibrare gli intervalli, **non** usati)

---

## 3. Automazione — la scheda di protocollo di collaudo

### Struttura reale

Il riferimento è la **IEC 62381** (*Automation systems in the process industry —
Factory acceptance test (FAT), site acceptance test (SAT), site integration
test (SIT)*). La norma è a pagamento, ma l'indice — che è quasi tutto quello che
serve — è leggibile nell'anteprima: 4 preparazione e documenti che ciascuna
parte porta, 5 FAT (piano di prova, procedura, *rework*, documentazione),
6 SAT, 7 SIT, e gli allegati A–J con il **rapporto di prova**, le *checklist* e
la **punch list**.

Due cose che la norma impone e che mancavano del tutto:

- **La punch list**: ogni punto aperto è classificato per *quando* si chiude —
  in loco, con ripetizione della prova, in sito prima del SAT, o come modifica
  concordata dopo il collaudo. Un numero di prove aperte senza categoria non è
  un deliverable.
- **La firma di entrambe le parti**: il certificato lo firmano il rappresentante
  del committente e quello del fornitore. Senza la firma del cliente il verbale
  non fa fede come accettazione.

Ordine reale della scheda: riferimento → tipo di collaudo (FAT/SAT) → commessa
e macchina → specifica di prova con revisione → versione software collaudata →
hardware (codice articolo PLC, blocchi di libreria) → esito delle prove →
punti aperti con categoria → prestazioni (tempo ciclo) → firme.

### Errori e imprecisioni tipiche

- La causa di una prova interrotta non finisce sul verbale.
- La versione del blocco di libreria non viene annotata.
- Una prova ripetuta viene registrata senza le condizioni iniziali.
- **Il cliente se ne va prima della fine e la firma manca**: è il buco più
  frequente e quello con più conseguenze.

### Vocabolario

Collaudo in fabbrica (FAT) e in sito (SAT), verbale, specifica di prova,
punti aperti / riserve, collaudo con riserva, presa in carico, tempo ciclo,
commessa, blocco di libreria, ricetta, fine corsa, asservimento, messa in
servizio.

### Che cosa è stato corretto

| Prima | Adesso | Perché |
|---|---|---|
| `6ES7-534-3AB89` | `6ES7315-5EB30-0XB0` | il codice MLFB Siemens non ha il trattino dopo `6ES7` e ha due gruppi finali; è la prima riga che un automatista legge |
| commessa `RIE-90` su un pallettizzatore | prefisso commessa legato alla macchina | contraddizione interna, vista in tre secondi |
| `FB_AxisMove v2.1` | `FB_Pallettizza V2.1.0`, `MC_MoveAbsolute (PLCopen)` | i blocchi di moto standard IEC 61131-3 si chiamano `MC_*`; le versioni di libreria si scrivono `V2.1.0` |
| nessun tipo di collaudo | `Tipo di collaudo: FAT (in fabbrica)` / `SAT (in sito)` | è il campo che definisce il documento (IEC 62381) |
| nessuna specifica di prova | `Specifica di prova: SPC-2026-082 rev. B` | il piano di prova è il presupposto del verbale |
| nessuna versione software | `Versione software collaudata: V2.9.8` | si collauda una versione, non «il software» |
| «prove ancora aperte: 3» | `Punti aperti: 3 — da chiudere in loco` | punch list dell'allegato H |
| nessuna firma | `Firma del tecnico` + `Firma del cliente` / `FIRMA CLIENTE ASSENTE` | il certificato lo firmano entrambe le parti |

Aggiunta la regola di casa 3.3 sui collaudi che si chiudono in CE-3: la
clausola che `m3-p3` cita («a metà della sezione 3, sui collaudi che si
chiudono con esito parziale») **non esisteva**, e il prompt di fallback non
poteva funzionare. Stesso difetto già trovato in numismatica il 01/09.

### Che cosa non si è trovato

- Il testo della IEC 62381 e della IEC 62337 (norme a pagamento). Si è lavorato
  sull'indice e sulle descrizioni pubbliche degli allegati; le categorie della
  punch list sono riportate come le descrive l'anteprima, non citate alla
  lettera.
- La documentazione ufficiale della struttura MLFB: Siemens l'ha ritirata dal
  pubblico intorno al 2018. La forma usata è quella ricostruita dalle fonti di
  settore e verificata su codici reali (`6ES7315-2AG10-0AB0`,
  `6ES7307-1EA00-0AA0`).

### Fonti

- IEC 62381:2012, anteprima con l'indice completo e gli allegati —
  <https://cdn.standards.iteh.ai/samples/18025/83cc1ac0c75145edabdc178b766f9979/IEC-62381-2012.pdf>
  (consultato 02/09/2026); edizione in vigore: IEC 62381:2024,
  <https://webstore.iec.ch/en/publication/67572>
- RINA, *Prove FAT, SIT, String e SAT* — terminologia italiana —
  <https://www.rina.org/it/fat-sit-string-and-sat-services> (consultato 02/09/2026)
- Kollmorgen, *PLCopen Function Blocks* — elenco dei blocchi `MC_*` —
  <https://webhelp.kollmorgen.com/kas3.07/Content/3.UnderstandKAS/Function%20Blocks.htm>
  (consultato 02/09/2026)
- Industrial Monitor Direct, *Decoding Siemens MLFB order numbers* — struttura
  ed esempi reali —
  <https://industrialmonitordirect.com/blogs/knowledgebase/siemens-plc-mlfb-order-number-structure-explained>
  (consultato 02/09/2026; fonte di settore, non ufficiale)

---

## 3-bis. Una correzione trasversale al kit

`pick_tradeoff()` in `generators/common.py` sceglieva i tre candidati di M2 uno
per criterio, ma senza escludere i **dominati**: in automazione usciva una
commessa che perdeva su tutti e tre i criteri contro un'altra in tabella. Un
candidato così non è un candidato, è un distrattore, e la stanza lo smonta
invece di discutere il compromesso. Adesso un candidato dominato viene saltato,
con ripiego sulla vecchia regola se non resta nulla.

## 4. Prompt da correggere in `demo-prompts.json`

Nessuno è stato modificato: sono stati rivisti uno a uno e non si toccano senza
segnalarlo. Queste tre righe adesso chiamano le cose con un nome che le schede
non usano più.

1. **`REFERENCE_FIELD_it`, numismatica** — oggi «Riferimento di catalogo». Sulla
   scheda quel nome ora indica il riferimento interno del lotto, che non è
   confabulabile. Dovrebbe diventare **«Riferimento bibliografico di catalogo»**:
   è quello che il modello inventa, ed è il perno del fallimento deliberato n. 1.
2. **`REFERENCE_FIELD_it`, fotovoltaico** — oggi «Riferimento del decreto
   sammarinese sull'incentivo e codice pratica». La scheda dice «Pratica Ufficio
   Energia». Da allineare, e da alleggerire sul decreto finché non si sa quale
   sia in vigore. Vale anche per la variante fotovoltaica di `m1-p2`.
3. **`m3-p5`, fotovoltaico** — chiede la tolleranza di calibrazione dei sensori
   di irraggiamento. Ora che l'irraggiamento è un campo della scheda, il
   recupero restituirà passaggi *vicini* alla domanda e nessuna tolleranza: il
   fallimento resta, e diventa più interessante da commentare. Nessuna modifica
   necessaria — solo da sapere prima di andare in aula.

## 5. Punto D — le fotografie

Non fatto in questa sessione, per scelta concordata. Restano da trovare e da
registrare con licenza: una moneta antica (esiste già), un modulo fotovoltaico
con la targhetta leggibile, un componente di automazione con la sua targhetta.
Destinazione `delivery/theory-deck/assets/img/` più un file di provenienza con
URL, autore, ente, licenza e data di consultazione per ciascuna.

## 6. Criteri di accettazione dell'handoff

- [x] Un professionista non trova niente di strutturalmente sbagliato — le
      correzioni sopra chiudono i casi trovati (asse di conio, riferimento
      bibliografico, catena del PR, MLFB, commessa/macchina, punch list, firme).
- [x] Le scale SM / RG / CE restano inventate e il modulo 3 continua a
      funzionare.
- [x] Tutti e tre i settori generano senza errori e `demo/` produce i ritagli
      per M1, M2 e M4.
- [x] Ogni affermazione ha una fonte; dove non c'è, è scritto che non c'è.
- [ ] Le tre fotografie con licenza (punto D) — aperto.

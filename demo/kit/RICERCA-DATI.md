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

---

## 7. Due settori aggiunti — `defi` e `associazione` (2026-09-08)

Aggiunti per le due lezioni del 14 settembre 2026. Stessa regola di prima:
**forma ricercata, valori inventati.**

### 7.1 DeFi — la scheda di rilascio

**Struttura reale.** Non esiste una scheda normata come la NU dell'ICCD o la
IEC 62381: la forma del documento si ricava dalle checklist di rilascio in uso.
I campi che ricorrono ovunque, e che il kit riproduce: indirizzo del contratto
e rete di destinazione, commit di rilascio, versione della strategia,
dipendenze esterne con la versione dichiarata nel lockfile, rilievi della
revisione divisi per gravità, copertura dei test, ritardo del timelock e soglia
del multisig, verifica del sorgente sull'explorer, riferimento del report di
revisione esterna.

**La gravità dei rilievi** si esprime nel mestiere con
`Critical / High / Medium / Low / Informational`: è la tassonomia delle società
di revisione, non una scala interna. È **la risposta che darà il gradino 1** del
modulo 3 — corretta in generale, e non quella della casa.

**Un dettaglio che vale un minuto in aula.** Un modello senza documenti cita
spesso lo *SWC Registry* come riferimento per le classi di vulnerabilità. La
home dello SWC Registry dice di sé: *«Please note, this content is no longer
actively maintained»*, non è aggiornata dal 2020, e rimanda a EEA EthTrust
Security Levels e a SCSVS. Quindi la risposta del gradino 1 è fluente, plausibile
e appoggiata a uno standard che si dichiara superato: è la dimostrazione di
`m3-p1` due volte, senza costi di preparazione.
Fonte: https://swcregistry.io/ (consultata 2026-09-08).

**Perché la scala RD è quella giusta da inventare.** Non ricalca la gravità dei
rilievi: **combina** rilievi aperti, copertura dei test e finestra di timelock in
un unico livello. Nessun modello può ricavarla, e un revisore la ricalcola a mano
in dieci secondi — che è esattamente ciò che serve alla verifica di D4.

**Non trovato / non verificato.** Le pratiche interne della software house
committente: chi firma un
rilascio, se esista uno standard interno scritto, quali reti usino davvero, se le
revisioni esterne siano pubblicate. Tutto quanto sopra è forma di settore, non
loro. Da chiedere prima della lezione.

### 7.2 Associazione di categoria — la scheda quesito

**Struttura reale.** Il documento è il registro dei quesiti dello sportello.
La forma è ricavata dai servizi che un'associazione di categoria sammarinese
dichiara pubblicamente: pratiche di inizio attività e licenze, contrattualistica
di lavoro, tabelle salariali, cassa integrazione, credito agevolato, libri paga,
contabilità e fiscale. Fonte: sito pubblico dell'associazione, consultato
2026-09-08. Il nome dell'organizzazione non è riportato qui: questo file viaggia
dentro il kit e dentro Banco.

**I riferimenti normativi nel config sono reali** — unica eccezione alla regola
del kit — e sono ripresi da un elenco di normativa pubblicato da un'associazione
di categoria sammarinese: L. 164/2022 (occupazione), DD 153/2023 (contratti a termine e
somministrazione), DD 105/2022 (formazione e politiche attive), L. 202/2020
(lavoro agile), L. 59/2016 (libertà sindacale e contrattazione), DD 50/2024
(attività economiche), L. 40/2014 (licenze), DD 11/2022 (lavoro autonomo senza
sede fissa), L. 157/2022 (previdenza), L. 118/2010 (stranieri), L. 129/2022
(famiglia). Fonte: elenco pubblico dell'associazione, consultato 2026-09-08.
Ognuna di queste norme è verificabile per numero e data sulla raccolta
ufficiale sammarinese: è la norma la fonte citabile, non l'elenco.

Sono reali per una ragione precisa: **il gradino 1 del modulo 3 sbaglia
giurisdizione, non merito.** Un modello senza documenti risponde con l'art. 2118
c.c., il D.Lgs. 81/2015 e un CCNL italiano — fluente, competente, altro Paese. La
dimostrazione funziona solo se la fonte giusta esiste davvero e sta scritta nei
documenti della casa. Nel config quesito e norma sono **appaiati per posizione**:
il quesito *i* cita la norma *i*, così la citazione regge alla lettura di chi quel
mestiere lo fa.

**La scala UA non misura la difficoltà del quesito: misura quanta verifica serve
e chi può firmare.** È una scala di responsabilità, ed è la ragione per cui questo
settore parla a un consiglio direttivo invece che a un ufficio.

**Non trovato / non verificato.** Se esista davvero un regolamento interno di
riscontro, come siano protocollati i quesiti, quali contratti collettivi siano
depositati per ciascun settore, e i tempi di riscontro reali. Il regolamento del
kit è **inventato**. Da chiedere prima della lezione.


---

## 8. Un settore aggiunto — `maglieria` (2026-09-12)

Il record è la **scheda di specifica**: una richiesta del committente
trasformata in specifica funzionale per il gestionale di produzione della casa.
Il settore è una software house che fa consulenza di processo e software
gestionale per maglifici, quindi il documento sta a cavallo di due mestieri e
deve reggere la lettura di entrambi.

### 8.1 Struttura reale — la parte software

**Struttura reale.** Lo standard di riferimento per che cosa deve contenere una
specifica di requisiti è **ISO/IEC/IEEE 29148:2018**, *Systems and software
engineering — Life cycle processes — Requirements engineering*. Il testo
«specifies the required processes implemented in the engineering activities that
result in requirements for systems and software products (including services)
throughout the life cycle», e in particolare definisce **gli information item
prodotti, il contenuto obbligatorio di ciascuno e le linee guida di formato**.
È la ragione per cui i campi obbligatori del kit sono undici e non cinque, e per
cui i criteri di accettazione sono un campo obbligatorio con una soglia (almeno
due, misurabili) e non una nota libera.
Fonte: <https://www.iso.org/standard/72089.html> (consultata 2026-09-12).
Il testo integrale è a pagamento; la pagina ISO pubblica scope e abstract, che
è quanto serviva qui.

**Che cosa NON è stato preso dallo standard.** Le forme correnti della pratica
agile — MoSCoW, punti storia, Given/When/Then, definition of done — sono
deliberatamente **fuori** dal regolamento della casa e compaiono solo come
risposta del gradino 1 in `generate_chain.py`. Sono la «media del settore» che
un modello senza documenti produce, ed è esattamente il salto che il modulo 3
deve rendere visibile.

### 8.2 Struttura reale — la parte maglieria

**Il ciclo di lavorazione.** L'ordine dei reparti nel config segue il ciclo
della maglieria calata come lo descrivono i maglifici stessi: sviluppo e
prototipo → **tessitura** → **rimaglio** → **rifinitura a mano** → **lavaggio**
→ **controllo qualità** → **stiro, etichettatura e imbusto**. Il conto lavoro
(terzisti) è trasversale.
Fonte: <https://www.rinaldicashmere.it/processo-produttivo-del-maglificio/>
(consultata 2026-09-12).

**Finezza.** La stessa fonte dichiara macchine rettilinee con finezze «da 12 a
5». Il config usa 7GG e 12GG, dentro l'intervallo dichiarato. La finezza è
scritta in GG accanto al tipo di telaio, come si scrive in reparto.

**Rimaglio.** È «la tecnica con la quale si cuciono insieme i "pezzi" del capo
di maglieria calata», su macchine diverse a seconda della finezza del filato, e
un singolo capo può richiedere più macchine. È lavorazione manuale, lenta e
specialistica — la ragione per cui è la fase che ogni maglificio sorveglia, e
per cui la scheda di D1 è una richiesta di avanzamento del rimaglio.
Fonte: ZoneModa, Università di Bologna, *Il mondo della maglieria e del
rimaglio* di Rosa Lucarelli,
<https://zonemoda.unibo.it/il-mondo-della-maglieria-e-del-rimaglio-di-rosa-lucarelli/>
(consultata 2026-09-12).

**Vocabolario tessile.** La terminologia di base della maglieria è normata da
**ISO 4921:2000**, *Knitting — Basic concepts — Vocabulary* (recepita come
BS EN ISO 4921:2002). Non è stata acquistata: è citata come la fonte normativa
del vocabolario, non come fonte dei valori.
Fonte: <https://www.iso.org/standard/33711.html> (consultata 2026-09-12).

Termini usati nel kit, nella forma che si usa in reparto: finezza in GG, titolo
del filato, consumo di filato a capo contro il consumo teorico di distinta,
**calo** di finissaggio, resa, cartellino di lavorazione, griglia taglie e
colori, conto lavoro e terzista, difettosità per tipo (buchi, cadute di maglia,
difetti di rimaglio), misure fuori tolleranza.

### 8.3 Che cosa non si è trovato — e che cosa ne consegue

**I tempi standard di fase non sono pubblici.** Nessuna fonte citabile pubblica
minuti a capo per tessitura, rimaglio, rifinitura, finissaggio o stiro: sono il
patrimonio industriale di ogni maglificio e il prodotto stesso di una
rilevazione tempi, cioè la cosa che una società di consulenza vende. Di
conseguenza:

* i **valori** in `min_capo` sono **inventati** e dichiarati tali;
* l'**ordine di grandezza relativo fra le fasi** segue il ciclo — tessitura la
  più lunga, poi rimaglio, poi rifinitura, poi finissaggio, stiro e controllo le
  più brevi — perché è l'ordinamento, non il numero assoluto, quello che un
  professionista verifica in tre secondi;
* **è l'unica cosa di questo pacchetto da far confermare al cliente prima
  della lezione.** Un ordinamento sbagliato fra le fasi si vede subito; un
  valore assoluto sbagliato è dichiarato sintetico e non costa nulla.

**Altro non verificato.** Quali moduli abbia davvero il gestionale del cliente,
come numeri le richieste, se esista uno standard interno di specifica scritto,
quali committenti abbia e come li codifichi. Tutto quanto sopra è forma di
settore, non loro. Da chiedere prima della lezione.

### 8.4 Perché la scala SP è quella giusta da inventare

Non ricalca nessuna scala di priorità esistente, e non per scelta estetica:
**MoSCoW e i punti storia misurano priorità e dimensione**, mentre la scala SP
misura *quanta specifica manca ancora alla richiesta e chi deve firmarla*. Si
ricalcola a mano leggendo tre campi in ordine — ambito dell'intervento, impatto
sul modello dati, stato dei dati di processo — e nessun modello senza documenti
può ricavarla.

Il livello che nessun quadro di priorità ha è **SP-5**: la richiesta cambia il
processo del committente e non il software, quindi non deve diventare un ticket.
È la posizione che una società di consulenza di processo sostiene per mestiere,
resa un campo obbligatorio di un documento.

### 8.5 Due righe collocate apposta

Documentate anche in cima a `generators/settori/maglieria.py`, perché un
cambio di seed non le rompa in silenzio:

* **riga 5 è l'unica SP-5.** Il fallimento voluto n. 2 abbassa la riga 5 della
  tabella di D4 di un livello, quindi la tabella presenta come «sospesa» una
  richiesta che non doveva diventare un ticket. Nella tabella la classe SP-4
  **non segue dai campi visibili** (l'impatto sui dati è «nuovo campo»): chi
  ricalcola vede che qualcosa non torna, ma per sapere *cosa* deve aprire la
  scheda, dove compare l'ambito «processo».
* **riga 7 è il record di D1 e D4.** SP-4, con dati di processo **rilevati** e
  criteri di accettazione inutilizzabili: gli appunti grezzi contengono tutto
  tranne la regola, quindi il modello che ci redige sopra assegna SP-1 o SP-2.

### 8.6 Il numero che compare tre volte

Nel record di D1 il tempo standard della fase compare in tre versioni diverse, e
non è un caso: quello che il modello **inventa** (8–15 minuti a capo, la media
di settore), quello che il capo reparto **dice a voce** (una cifra tonda, sotto
il vero), e quello che la **rilevazione ha misurato** (il valore in
`ground-truth.csv`). La regola 2 della casa esiste per la distanza fra gli
ultimi due; il modulo 1 esiste per la distanza fra il primo e gli altri due.

# Guida rapida alla scala SP

*Promemoria operativo per lo staff. Estratto del regolamento, sezione 1.*

Si leggono tre campi, in quest'ordine: ambito dell'intervento, impatto sul modello dati, stato dei dati di processo. Il primo che si applica decide la classe. In caso di dubbio fra due livelli adiacenti si assegna sempre il livello **più alto**, cioè il più prudente, e il dubbio va annotato nel campo note.

## SP-1 — Specifica diretta

L'intervento resta nel software, non tocca il modello dati e i dati di processo del reparto sono stati rilevati: la specifica si chiude con la firma del solo revisore ed entra in stima.

## SP-2 — Specifica assistita

L'intervento resta nel software e i dati di processo sono rilevati, ma introduce un nuovo campo: prima della stima serve una conferma con il committente sul significato del campo e su chi lo compila.

## SP-3 — Specifica da rilevare

I dati di processo sono dichiarati dal committente oppure non disponibili: la specifica non si chiude finché non è stata fatta la rilevazione in reparto, e la stima resta NON STIMABILE.

## SP-4 — Specifica sospesa

L'intervento modifica record già in produzione: servono l'approvazione scritta del committente e la firma di un secondo revisore prima che la specifica entri in sviluppo.

## SP-5 — Fuori specifica

La richiesta cambia il processo del committente e non il software: non diventa un ticket e torna al committente come proposta di intervento sul processo, mai come stima.

## Errori frequenti

- Assegnare SP-1 quando il tempo di fase è stato riferito a voce e non rilevato: un dato dichiarato porta la scheda a SP-3, qualunque sia l'impatto sul modello dati.
- Usare SP-5 come sinonimo di «richiesta rifiutata»: SP-5 dice che l'intervento non è software, non che non vada fatto.
- Confondere NON DEFINITI con SP-3: i criteri di accettazione mancanti bloccano la stima, non la classe.
- Assegnare SP-2 a una modifica di record già in produzione perché «è solo un campo»: toccare dati esistenti è SP-4.
- Scrivere il nome del maglificio al posto del codice cliente perché «tanto è una bozza interna»: la bozza è il documento che poi viene allegato.

---

_Documento sintetico generato per formazione — non usare in produzione._

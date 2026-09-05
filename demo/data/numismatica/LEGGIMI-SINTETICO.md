# Dati sintetici per la lezione — Casa d'Aste Sammarinese

**Nessuno di questi documenti è reale.** Sono generati automaticamente per una
dimostrazione didattica. La scala interna e il regolamento sono **inventati**:
servono a rendere evidente quando un modello risponde davvero a partire dai
vostri documenti e quando sta improvvisando. Sono inventati anche i campi di
giudizio usati nel modulo 2 — dove il criterio non è misurabile dal documento,
il valore è sintetico e va trattato come tale.

| Cartella | Contenuto | Usata in |
|---|---|---|
| `regole/` | regolamento interno e guida alla scala (`.md` + `.pdf`) | M3 — grounding |
| `lotti/` | 12 schede di lotto in PDF | M4 — compito su cartella |
| `avvelenata/` | le stesse schede + una con istruzione nascosta | M5 — prompt injection |
| `demo/` | ritagli pronti da incollare | M1, M2, M4 |
| `_perito/` | risposte corrette (CSV) | M4 — verifica, **solo per il docente** |

Non puntare l'agente su `_perito/`: contiene le risposte.

La scheda `avvelenata/lotto-047.pdf` contiene un'istruzione nascosta
in grigio chiarissimo, corpo 4,6. È volutamente innocua: chiede solo di
elencare file. Aprire il PDF e selezionare tutto il testo per mostrarla alla
platea.

Rigenerare con: `python generate.py --settore numismatica` (stesso seed → stessi
documenti).

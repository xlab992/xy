# 📺 Script per Liste M3U Italiane Personalizzate 🇮🇹

Questo repository contiene script Python per generare automaticamente liste M3U di canali televisivi italiani, con un focus sugli eventi sportivi e la possibilità di utilizzare un proxy per una maggiore stabilità dei flussi.

Si possono utilizzare due proxy, proxydd,tvproxy e mediaflow proxy
per OMG consiglio Mediaflow, a breve uscirà una versione che consentirà di far partire anche i flussi HAT (H) e (Hd) e Thisnot (TN)

**Link ai proxy**

https://github.com/mhdzumair/mediaflow-proxy

Pigzilla

https://github.com/MarkMCFC/tfms.xyz


per far girare anche i link HAT andarà installata una versione diversa di Mediaflow, quando sarà disponibile aggiornerò il readme

## ✨ Liste M3U Disponibili

Una volta configurati ed eseguiti gli script e i workflow GitHub Actions, avrai a disposizione le seguenti liste:

*   🌍 **TUTTE le liste in un file solo:**
    *   `listone.m3u8`


      
*   🇮🇹 **Canali Italiani Generali da DaddyLive con Hattrick e Skystreaming:**
    *   `247ita.m3u8`
*   🇮🇹 **Canali Italiani Filtrati da Vavoo:**
    *   `channels_italy.m3u8`
*   ⚽ **Eventi Sportivi Maggiori (Misto ITA/Internazionale):**
    *   `itaevents.m3u8`
*   🏆 **Eventi Sportivi Maggiori (Solo Flussi Italiani):**
    *   `fullita.m3u8`
*   🌍 **TUTTI gli Eventi Sportivi (Molto Estesa):**
    *   `onlyevents.m3u8`
---

## 🛠️ Configurazione Iniziale degli Script

Prima di poter generare le liste, è necessario configurare alcuni parametri negli script Python.

### 1. Script Basati su DaddyLive

Modifica il file:
*   `.env`
  
    Il file ENV ora è diviso per siti, quindi scegliete per ogni sito il tipo di proxy che volete scegliere

  
## ⚙️ Configurazione e Esecuzione dei Workflow GitHub Actions
Dopo aver modificato e committato gli script sul tuo repository GitHub:

1. Vai alla sezione Actions del tuo repository: https://github.com/TUO_USER_GITHUB/NOME_TUO_REPOSITORY/actions (Sostituisci TUO_USER_GITHUB e NOME_TUO_REPOSITORY con i tuoi dati).
2. Se i workflow non sono attivi, abilitali.
3. Vai su Settings del tuo repository: https://github.com/TUO_USER_GITHUB/NOME_TUO_REPOSITORY/settings
4. Nel menu a sinistra, clicca su Actions e poi su General .
5. Scorri fino alla sezione "Workflow permissions".
6. Seleziona l'opzione Read and write permissions .
7. Clicca su Save.

   
### Esecuzione dei Workflow (solo la prima volta, poi va in automatico)
Torna alla sezione Actions . 

Esegui il workflow nel seguente ordine:

1. 🚀 1 unified :
   - Clicca sul nome del workflow.
   - Sulla destra, clicca su "Run workflow".
   - Conferma cliccando sul pulsante verde "Run workflow".

8. ⏳ ATTENDI IL COMPLETAMENTO del workflow precedente (deve apparire una spunta verde ✅).

     
9. (Opzionale) 🌍1 Update OnlyEvents :
   - Se desideri la lista con TUTTI gli eventi sportivi (molto estesa e potenzialmente con sport di nicchia), esegui anche questo workflow dopo il completamento degli altri.
Attendi che tutti i workflow selezionati abbiano una spunta verde ✅. Questo indica che le liste M3U sono state generate e aggiornate nel tuo repository.

Per i giorni a seguire non serve fare nulla, partono in automatico, mettere l'aggiornamento delle playlist su OMG ogni ora


## 🔗 Usare la lista con OMG
Per utilizzare le liste generate basta andare ad inserire il link raw del file listone.m3u8

   
## 🔌 Utilizzo con OMG (o altre applicazioni)
1. Apri la tua applicazione (es. OMG).
2. Nel campo per l'inserimento dell'URL della lista M3U, incolla l'indirizzo link Raw di listone.m3u8.
3. Abilita l'opzione per l'EPG senza link.
5. Procedi con la generazione della configurazione o l'installazione dell'addon, come richiesto dalla tua applicazione.
🎉 Fatto! Ora dovresti avere accesso ai canali tramite le tue liste M3U personalizzate e auto-aggiornate.

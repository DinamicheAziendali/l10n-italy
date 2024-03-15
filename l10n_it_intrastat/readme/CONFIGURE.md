**Italiano**

In _Impostazioni → Utenti e aziende → Aziende → Nome azienda_ impostare i parametri
delle seguenti sezioni presenti nella scheda "Informazioni generali".

1.  Intrastat
    1.  _ID utente (codice UA)_: inserire il codice identificativo Intrastat
        dell’azienda (codice alfanumerico di 4 caratteri, utilizzato come identificativo
        per l’accesso alle applicazioni delle Dogane).
    2.  _Unità di misura per kg_: parametro che indica l’unità di misura che viene
        verificata sulla riga fattura soggetta a Intrastat. Se sulla riga il peso è
        espresso nell’unità di misura indicata nel parametro (o in un suo multiplo), il
        peso che viene riportato nella corrispondente riga Intrastat è quello preso
        dalla riga fattura.
    3.  _Unità supplementare da_:
        1.  _peso_: da peso dei prodotti sulla riga Intrastat
        2.  _quantità_: da quantità dei prodotti sulla riga Intrastat
        3.  _nulla_
    4.  _Escludere righe omaggio_: esclude dalle righe Intrastat le righe a valore 0.
    5.  _Delegato_: il nominativo della persona delegata alla presentazione della
        dichiarazione Intrastat.
    6.  _Partita IVA delegato_: la partita IVA della persona delegata alla presentazione
        della dichiarazione Intrastat.
    7.  _Nome file da esportare_: nome del file che può essere impostato per forzare
        quello predefinito (SCAMBI.CEE).
    8.  _Sezione doganale_: sezione doganale predefinita da proporre in una nuova
        dichiarazione.
    9.  _Ammontare minimo_: in caso di fatture di importo inferiore usa questo valore
        nella dichiarazione.
2.  Valori predefiniti per cessioni (parametri Intrastat per le fatture di vendita)
    1.  _Forzare valore statistico in euro_: casella di selezione attualmente non
        gestita.
    2.  _Natura transazione_: indica il valore predefinito che verrà impostato nelle
        righe Intrastat di una fattura per il campo di riferimento.
    3.  _Condizioni di consegna_: indica il valore predefinito che verrà impostato nelle
        righe Intrastat di una fattura per il campo di riferimento.
    4.  _Modalità di trasporto_: indica il valore predefinito che verrà impostato nelle
        righe Intrastat di una fattura per il campo di riferimento (Modo di trasporto).
    5.  _Provincia di origine_: indica il valore predefinito che verrà impostato nelle
        righe Intrastat di una fattura per il campo di riferimento (provincia di origine
        della spedizione dei beni venduti).
3.  Valori predefiniti per acquisti (parametri Intrastat per le fatture di acquisto)
    1.  _Forzare valore statistico in euro_: casella di selezione attualmente non
        gestita.
    2.  _Natura transazione_: indica il valore predefinito che verrà impostato nelle
        righe Intrastat di una fattura per il campo di riferimento.
    3.  _Condizioni di consegna_: indica il valore predefinito che verrà impostato nelle
        righe Intrastat di una fattura per il campo di riferimento.
    4.  _Modalità di trasporto_: indica il valore predefinito che verrà impostato nelle
        righe Intrastat di una fattura per il campo di riferimento (Modo di trasporto).
    5.  _Provincia di destinazione_: indica il valore predefinito che verrà impostato
        nelle righe Intrastat di una fattura per il campo di riferimento (provincia di
        destinazione della spedizione dei beni acquistati).

**Tabelle di sistema**

In _Fatturazione/Contabilità → Configurazione → Intrastat_ sono presenti le funzionalità
per la gestione delle tabelle di sistema.

- Sezioni doganali
- Nomenclature combinate
- Modalità di trasporto
- Natura transazione

Tali tabelle sono pre-popolate in fase di installazione del modulo, in base ai valori
ammessi per le dichiarazioni Intrastat.

N.B.: Il sottomenù "Intrastat" è visibile solo se vengono abilitate le funzionalità
contabili complete.

**Posizione fiscale**

L'assoggettamento ad Intrastat può essere gestito anche a livello generale di singolo
partner, associandogli una posizione fiscale che abbia l'apposita casella "Soggetta a
Intrastat" selezionata.

Tutte le fatture create per il partner che ha una posizione fiscale marcata come
soggetta ad Intrastat avranno l’apposito campo "Soggetta a Intrastat" selezionato
automaticamente.

**Prodotti e categorie**

La classificazione Intrastat dei beni o dei servizi può essere fatta sia a livello di
categoria che a livello di prodotto.

La priorità è data al prodotto: se su un prodotto non è configurato un codice Intrastat,
il sistema tenta di ricavarlo dalla categoria a cui quel prodotto è associato.

Per il prodotto la sezione Intrastat si trova nella scheda «Fatturazione/Contabilità»,
ove è necessario inserire:

- la tipologia (Bene, Servizio, Varie, Escludere);
- il codice Intrastat, tra quelli censiti tramite l’apposita tabella di sistema
  "Nomenclature combinate" (il campo viene abilitato solo per le tipologie "Bene" e
  "Servizio").

Per le categorie di prodotti, le informazioni sono presenti in un’apposita area
Intrastat della maschera di dettaglio.

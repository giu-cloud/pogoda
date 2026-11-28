# Lens: vento ad alta definizione su un riquadro

**Lens** prende la previsione di un modello meteo e la ridisegna su un riquadro scelto, con il rilievo vero, a una maglia di 150-300 m. Il risultato sono il vento e le raffiche a 10 m, ora per ora, con ridossi, accelerazioni, aggiramenti dei rilievi e la fascia di vento frenato lungo le coste sottovento.

Non è un modello fisico completo come WRF: non crea fenomeni che il modello di partenza non ha. Ridistribuisce il vento del modello sul terreno vero rispettando la conservazione della massa, e aggiunge stime fisiche per ciò che la conservazione della massa non vede. Costa minuti invece di ore, ed è questo che lo rende usabile a bordo.

Nato il 20/11/2026 sui golfi di Palermo e Mondello. Codice nel deposito `giu-cloud/nowica`, cartella `lens/`.

## Il metodo, in sette passi

1. **Terreno.** Rilievo Copernicus DEM a 30 m e uso del suolo ESA WorldCover. La rugosità z0 va da 0,0002 m in mare a 0,6 nel bosco e 0,8 in città. La griglia è regolare in latitudine e longitudine, quindi l'uscita è già un GRIB normale. Attorno al riquadro chiesto si aggiunge da solo un margine (almeno 2,5 km, o il 6% del lato), perché i rilievi appena fuori decidono il vento dentro.

2. **Modello di partenza, letto in due modi.**
   - Vento e raffica a 10 m due volte: con le celle di mare per il mare e con quelle di terra per la terra. Così vicino alla costa il vento di mare non arriva già sporcato dalla terra del modello, e l'effetto della costa lo calcola Lens alla sua maglia.
   - Profilo verticale del modello su 8 livelli di pressione (da 1000 a 700 hPa, cioè fino a circa 3000 m), punto per punto: vento, direzione, temperatura, quota.
   - I livelli che il modello non dà vengono saltati.

3. **Campo di partenza in 3D.**
   - Fino a 100 m dal suolo: profilo logaritmico dal vento a 10 m, con la rugosità del punto.
   - Sopra: il profilo del modello interpolato in quota assoluta, punto per punto.
   - Tra 100 e 400 m dal suolo: raccordo tra i due.
   - Livelli di 20 m dal mare fino a 1200 m, poi sempre più larghi fino a oltre 3000 m.

4. **Stabilità a due strati.**
   - Dalla pendenza della temperatura potenziale del modello si ricava il numero di Froude (Fr = U / N H, con H la quota dei rilievi più alti) in due strati: dal suolo alla cima dei rilievi, e da lì a 2,5 volte quella quota.
   - Con aria stabile salire costa e il vento aggira i rilievi; con aria rimescolata li scavalca. Il peso del moto verticale nel passo 5 è alfa² = Fr², tra 0,03 e 1,5.
   - Un caso tipico è l'inversione bassa di una mattina con aria rimescolata sopra: in basso il vento aggira, in alto passa.

5. **Conservazione della massa (Sherman 1978, lo stesso principio di WindNinja).** Si cerca il campo di vento più vicino a quello di partenza che non attraversi il terreno e non crei né distrugga aria. È un'equazione di Poisson per un moltiplicatore, risolto con un multigrid algebrico. La divergenza residua scende di 4-5 ordini di grandezza.

6. **Vento a 10 m e due stime fisiche.**
   - Il vento a 10 m dal suolo si ricava con il profilo logaritmico della rugosità locale.
   - **Ridosso sottovento:** si misura l'angolo sotto cui si vede il rilievo sopravvento (parametro di Winstral). Con aria stabile e vento debole la scia si allunga, fino a 3 volte; con vento teso si accorcia. È il comportamento osservato da Giano a Stromboli.
   - **Frenata della costa:** il vento che arriva da terra è frenato dalla rugosità. In mare riaccelera man mano che sotto si forma uno strato liscio, alto δ = c · z0^0,2 · x^0,8 (Elliott), fino a 200 m. La fascia frenata è larga 1-3 km, più lunga con aria stabile.
   - Le due stime non si sommano: conta la più forte.
   - I puntini sulla carta segnano dove un ricircolo è probabile.

7. **Raffiche.**
   - Si calcolano dall'intensità di turbolenza locale (1 / ln(10/z0)).
   - In mare vicino alla costa la turbolenza portata da terra si smorza più piano del vento medio; nella scia dei rilievi cresce.
   - Il fattore di picco si tara a ogni ora sul rapporto tra raffica e vento medio che il modello stesso dà in mare aperto, a più di 5 km dalla costa. Al largo Lens dà quindi le stesse raffiche del modello, e sotto costa le varia.

## Che cosa NON fa

- Non crea brezze, termiche di versante o venti catabatici: c'è solo la brezza che dà il modello.
- Non disegna i vortici di scia: ne indica la zona.
- Non corregge gli errori di tempo del modello: se il modello sbaglia l'ora in cui entra il maestrale, Lens la sbaglia uguale, con più dettaglio.
- Le costanti del ridosso, della fascia costiera e della turbolenza di scia sono stime della letteratura, non ancora tarate con anemometri veri.

## Costi misurati (macchina gratuita di GitHub, 2 processori, 7 GB)

- **Palermo e Mondello, 20/11/2026:** riquadro di 38 x 44 km, dominio di calcolo 43 x 49 km a 150 m. 6 milioni di celle d'aria e 4,8 GB di memoria.
- **Tempi:** circa 3 minuti per leggere terreno, OpenStreetMap e modello (con due pause per il limite di Open-Meteo). Poi 50 secondi per la prima ora e circa 30 per le altre; un minuto quando cambia la stabilità. In tutto 12 minuti per 15 ore, 10 per 6 ore.
- **Divergenza:** dopo l'aggiustamento scende di circa 40.000 volte, da 8·10⁻⁴ a 2·10⁻⁸ s⁻¹.
- **Più rapido (23/11):** il risolutore si ferma a una tolleranza di 5·10⁻³ invece di 10⁻⁵ e la matrice non si rimonta a ogni ora. Sulle Eolie (7,2 milioni di celle) un'ora dopo la prima passa da circa 43 a 17-18 secondi; il vento a 10 m sul mare cambia al più di 0,02 nodi (99 % delle celle sotto 0,01). La divergenza scende di circa 30 volte invece che di migliaia, ma l'errore che resta è di un millimetro al secondo. L'atlante resta a 10⁻⁵, perché si calcola una volta sola. Per tornare a prima: `LENS_TOL=1e-5`.
- **Raffiche al largo:** coincidono con quelle del modello (rapporto 1,29-1,55 con il vento medio), per costruzione. Sotto costa il rapporto arriva a 2-2,5 dove il vento esce da terra o da una scia, con un tetto a 2,6.
- **Maglia:** si sceglie da sola, la più fitta che sta in memoria (circa 100.000 colonne), mai sotto i 150 m. Per un riquadro di 100 x 70 km, come le Eolie, viene circa 250 m.
- **Limite di Open-Meteo:** ogni punto conta come una richiesta, con un tetto di 600 al minuto, e le letture sono distanziate di un minuto. ICON-2I dà il profilo verticale su 4 livelli (1000, 925, 850, 700 hPa); i livelli mancanti si saltano.

## Uscite

- **Pagina HTML** da scorrere ora per ora, con la grafica di Shift: tinte per quota, ombreggiatura, curve brune, frecce sottili colorate con la scala del vento di Shift. A richiesta: campitura, banderuole, raffiche, differenza con il modello. Il tocco mostra nodi, forza, direzione, raffica.
- **GRIB2** su griglia regolare lat/lon: 10u, 10v e raffica (parametro 22) a 10 m, un messaggio per ora, centro "non specificato". Si apre come qualsiasi altro GRIB. Finisce nella release `lens` del deposito.

## Come lanciarlo oggi

Su github.com, deposito `nowica` → Actions → lens → Run workflow. Le caselle:

- **area:** S,N,O,E in gradi, per esempio `38.30,38.90,14.20,15.30` per le Eolie; vuota per Palermo;
- **nome:** il titolo della pagina;
- **modello:** di partenza (vuoto = ICON-2I; poi ICON-EU, ECMWF);
- **ore** e **da:** prima ora contata da adesso;
- **dx:** la maglia, se la si vuole imporre.

## Come alleggerirlo

Il metodo è lineare. Con la stabilità fissata, l'aggiustamento a conservazione di massa (passo 5) trasforma il campo di partenza con un'operazione lineare: la risposta del rilievo a una somma di venti è la somma delle risposte. Da qui due strade.

### 1. Ritocchi alla versione completa (da 12 a circa 5-6 minuti per 15 ore)

- **Deposito pubblico:** spostare Lens nel deposito pubblico `shift-grib`. Lì i minuti sono gratuiti e la macchina ha 4 processori e 16 GB: più veloce, e la maglia può scendere sotto i 150 m.
- **Lettura del modello:** prendere ICON-2I dai quadratini che il server di Shift scarica già, invece che da Open-Meteo. Spariscono le due pause da un minuto per il limite di richieste.
- **Terreno in cache:** rilievo, uso del suolo e nomi salvati una volta per area.
- **Un'ora su due:** calcolare ogni 2 ore e interpolare nel tempo. Grazie alla linearità, tra due ore con la stessa stabilità l'interpolazione è quasi esatta.
- **Tolleranza:** fatto il 23/11 (5·10⁻³, vedi i costi misurati).

### 2. Atlante di Lens: calcolo una volta per area, poi istantaneo sul tablet

- **Risposte di base:** per ogni area si calcola in anticipo come il rilievo risponde a quattro venti unitari: da est e da nord, vicino al suolo e in quota. Si fa per 4 classi di stabilità: 16 calcoli, circa 15 minuti su GitHub, una volta sola.
- **Peso:** il risultato, cioè 8 campi per classe, pesa circa 6 MB per un'area come i golfi di Palermo, e si scarica una volta.
- **Uso:** sul tablet, per ogni ora e ogni punto, il vento fine è la combinazione delle quattro risposte, pesata con il vento del modello in quel punto. Poi Shift aggiunge ridosso, fascia costiera e raffiche, che sono calcoli leggeri (in Kotlin, pochi secondi).
- **Risultato:** 15-24 ore in pochi secondi, senza rete, su qualsiasi GRIB caricato, anche in mare.
- **Cosa si perde:** il vento del modello viene trattato come uniforme alla scala dei rilievi vicini (in pratica si usa il valore locale), e il profilo verticale si riduce a due strati. Lo scarto rispetto alla versione completa va misurato sulle stesse ore di Palermo prima di adottarlo.
- **Aree frequenti:** si preparano in anticipo, per esempio golfi di Palermo, Eolie, Egadi, Bocche di Bonifacio, golfo di Napoli. Per un'area nuova si costruisce l'atlante a richiesta, oppure si lancia la versione completa.

## Come trasporlo in Shift

1. **Due modi nello stesso tasto Lens.**
   - **Atlante:** per le aree già preparate, il calcolo è sul tablet, istantaneo e senza rete.
   - **Completo:** per le aree nuove, o quando si vuole il profilo verticale ora per ora, il calcolo gira sul server GitHub di Shift (8-15 minuti; meglio nel deposito pubblico `shift-grib`).
   - Il calcolo completo non va sul tablet: servono quasi 5 GB di memoria e un risolutore multigrid.
2. **Comando nell'app.** Un tasto **Lens** in Data/Weather, accanto a Get GRIB:
   - si traccia il riquadro sulla carta, come per scaricare un GRIB, anche lungo un routing (per esempio sulle Eolie);
   - si sceglie il modello di partenza tra quelli che coprono l'area, con l'elenco già usato in Get GRIB;
   - si scelgono l'ora di inizio e quante ore (default 6, massimo 24);
   - prima di lanciare l'app mostra la maglia che verrà, se c'è un atlante pronto, il tempo stimato e i minuti di GitHub che consuma.
3. **Avvio.** L'app lancia il workflow con la REST API (`POST /repos/{owner}/{repo}/actions/workflows/lens.yml/dispatches`, gli stessi parametri delle caselle). Il token di Shift deve avere anche il permesso "Actions: write": oggi legge solo le release.
4. **Notifiche (richiesto da Giano il 20/11).** L'app deve poter mandare notifiche di sistema Android, perché il calcolo completo dura minuti e nel frattempo il tablet fa altro o ha lo schermo spento:
   - all'avvio: "Lens partito: <area>, <modello>, <ore>, pronto tra circa N minuti";
   - alla fine: "Lens pronto: <area>". Toccando la notifica si apre Shift sulla carta con Lens già caricato;
   - in caso di errore: "Lens non riuscito" con il motivo in una riga (modello non disponibile, area troppo grande, rete);
   - anche per la costruzione di un atlante, e per lo scaricamento di un atlante quando finisce.
   - Tecnica: un lavoro in background (WorkManager) controlla lo stato del calcolo sul server ogni 30-60 secondi, poi scarica il GRIB e pubblica la notifica. Se il telefono o il tablet sono senza rete, riprova quando torna. Serve il permesso di notifica (Android 13 e oltre) e un canale "Lens".
   - Le stesse notifiche andranno poi all'orologio, come le altre di Shift in navigazione.
   - Nella pagina delle notifiche di Shift resta l'elenco dei calcoli Lens fatti.
5. **Arrivo.** L'app scarica il GRIB dalla release (un file per lancio, con data e area nel nome) e lo apre come un modello in più, chiamato "Lens · <modello di partenza>", legato al Passage se è attivo.
6. **Routing.** Dentro il riquadro usa Lens, fuori il modello di partenza, con un raccordo sui bordi. Con Lens attivo, le ombre e accelerazioni stimate da Shift si spengono dentro il riquadro, perché lì sono calcolate.
7. **Rotta ideale e verifica in navigazione.** Lens entra come una previsione in più, con lo stesso trattamento degli altri GRIB.

## Confronti con osservazioni

- **20/11/2026, verso le 17 locali (16 UTC), poco fuori dal porto di Palermo, vento da ovest.** Dato riferito a Giano da chi era in barca: media 10-11 nodi, direzione giusta, raffiche intorno a 20 nodi (non si sa se tutte o la più forte). Lens (ICON-2I, lancio delle 16:07 UTC) dava: all'imboccatura 6-8 nodi con raffiche 9-11; a 2-3 km 10 nodi con raffiche 14; a 5 km 12-13 con raffiche 17. ICON-2I al largo dava un rapporto raffica/media di circa 1,37. Indicazioni, da confermare con altri dati: la frenata della città sotto costa forse è troppo forte, e le raffiche con vento che esce dalla città (e dai monti dietro) sono sottostimate, già nel modello di partenza.

## Possibili miglioramenti successivi

- **Taratura con anemometri veri** (MeteoNetwork, ISPRA, SIAS, aeroporti): lunghezza dei ridossi, larghezza della fascia costiera, fattore di picco delle raffiche.
- **Venti termici:** brezze di versante e catabatici (il terrale notturno che scende dalle valli, come l'Oreto) con una parametrizzazione dal bilancio radiativo.
- **Celle tagliate o coordinate che seguono il terreno,** al posto della griglia a scalini: meno rumore sui pendii senza bisogno di lisciare.
- **Insieme di modelli di partenza** (ICON-2I, ECMWF, AROME dove c'è): la dispersione dice dove fidarsi.
- **Solutore con la quantità di moto** (come WindNinja con OpenFOAM) per scie e ricircoli veri: molto più costoso, da valutare solo se i dati lo chiedono.


## Correzioni del 20/11 sera (dopo la prima prova sulle Eolie)

- **Stabilità:** la temperatura a 2 m non entra più nel calcolo di N (sul mare d'autunno è più calda dell'aria e dava Fr 9,9 fisso). N viene dalla differenza di temperatura potenziale tra i livelli del modello che racchiudono lo strato, con un minimo efficace di 0,010 1/s e un massimo di 0,030. alfa2 al più 1.
- **Strato bloccato:** alfa2 = 0,005 sotto la linea divisoria Hd = H (1 − Fr), con Hd mai sotto metà del rilievo (ipotesi: i fianchi ripidi delle isole staccano il flusso anche con vento teso). Tra Hd e la cima alfa2 = Fr² tra 0,06 e 0,5; sopra, Fr² dello strato alto tra 0,25 e 1. H è la quota che fa da sbarramento: il massimo tra il 98° percentile della terra e l'85% della cima più alta.
- **Modello di partenza lisciato** su circa 4 km (filtro gaussiano) prima di entrare in Lens.
- **Scia:** piena sopra 11,5° di angolo e nulla sotto 1,5° (38 volte l'altezza), distanze divise per 1/Fr tra 0,8 e 3. Tarata su Lipari, Alicudi e Stromboli.

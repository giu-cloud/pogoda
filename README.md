# pogoda

Previsione meteo locale per due posti in montagna in Polonia (Nowica e Fiodor's place), costruita sopra i modelli meteo aperti e aggiornata ogni 3 ore.

- `archivio/`: osservazioni IMGW e previsioni dei modelli salvate a ogni giro.
- `previsione/`: combinazione dei modelli, correzione di quota, avvisi, pagina in polacco e italiano.
- `mappa/`: carte di base e campi della mappa.
- `sito/`: icone e preparazione delle pagine pubblicate.

Le coordinate stanno solo nei Secrets del deposito.

## Fonti dei dati e attribuzioni
- Osservazioni: IMGW-PIB (danepubliczne.imgw.pl). Źródłem pochodzenia danych jest Instytut Meteorologii i Gospodarki Wodnej – Państwowy Instytut Badawczy.
- Previsioni: Open-Meteo.com (CC BY 4.0), che ridistribuisce i modelli di DWD, ECMWF, NOAA, Météo-France, CHMI, DMI, KNMI e altri.
- Rilievo: Copernicus DEM GLO-30 © DLR e Airbus, fornito nell'ambito del programma Copernicus.
- Uso del suolo: ESA WorldCover 2021 (CC BY 4.0).
- Fiumi, strade, località: © OpenStreetMap contributors (ODbL).
- Carattere delle scritte della carta: EB Garamond (SIL Open Font License 1.1, testo in `previsione/fonti/OFL.txt`).

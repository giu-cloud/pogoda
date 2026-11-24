"""Funzioni comuni: coordinate dai Secrets, richieste web, distanze.
Le coordinate della casa non vanno mai stampate ne' scritte nei file."""
import json, math, os, sys, time, urllib.request, urllib.error

UA = {"User-Agent": "meteo-casa/0.1 (progetto personale non commerciale)"}


# Le case seguite. Ognuna ha i suoi Secrets (PREFISSO_LAT, PREFISSO_LON, PREFISSO_QUOTA) e le sue cartelle.
# La casa in lavorazione si sceglie con la variabile SITO (a, b, ...).
SITI = {
    "a": {"prefisso": "CASA", "lati": [150, 50, 20], "titolo": {"pl": "Nowica", "it": "Nowica"}, "casa": {"pl": "Dom", "it": "Casa"}},
    "b": {"prefisso": "FIODOR", "lati": [60, 20, 7], "titolo": {"pl": "Fiodor's place", "it": "Fiodor's place"}, "casa": {"pl": "Fiodor's place", "it": "Fiodor's place"}},
}
SITO = os.environ.get("SITO", "a")
CFG = SITI[SITO]
SUF = "" if SITO == "a" else "_" + SITO  # suffisso delle cartelle: dati, dati_b, ...


def _num(nome, obbligatorio=True):
    v = (os.environ.get(nome) or "").strip().replace(",", ".")
    if not v:
        if obbligatorio:
            sys.exit(f"Manca il Secret {nome}: Settings > Secrets and variables > Actions")
        return None
    return float(v)


def casa():
    """(lat, lon, quota o None)"""
    pre = CFG["prefisso"]
    if not (os.environ.get(pre + "_LAT") or "").strip() and SITO != "a":
        print(f"sito {SITO}: mancano i Secrets {pre}_LAT e {pre}_LON, salto")
        sys.exit(0)
    return _num(pre + "_LAT"), _num(pre + "_LON"), _num(pre + "_QUOTA", False)


def scarica(url, timeout=40, tentativi=2, grezzo=False):
    """Ritorna (stato, contenuto). Non solleva eccezioni: l'errore torna come testo."""
    ultimo = "?"
    for i in range(tentativi):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                dati = r.read()
                return r.status, (dati if grezzo else dati.decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            corpo = e.read()[:400].decode("utf-8", "replace")
            ultimo = f"HTTP {e.code}: {corpo}"
            if e.code in (400, 403, 404):
                return e.code, ultimo
        except Exception as e:  # rete, timeout
            ultimo = f"{type(e).__name__}: {e}"
        time.sleep(3 * (i + 1))
    return 0, ultimo


def scarica_json(url, **kw):
    stato, testo = scarica(url, **kw)
    if stato != 200:
        return stato, testo
    try:
        return 200, json.loads(testo)
    except Exception as e:
        return 0, f"JSON non valido: {e}"


def km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def pulisci(testo, lat, lon):
    """Toglie le coordinate della casa da un testo (URL negli errori, ecc.)."""
    t = str(testo)
    for v in (lat, lon):
        for n in (7, 6, 5, 4, 3, 2):
            t = t.replace(f"{v:.{n}f}", "***")
        t = t.replace(str(v), "***")
    return t


# Modelli da provare su Open-Meteo (nome API: descrizione). I nomi non validi
# vengono segnalati dalla ricognizione e poi tolti.
MODELLI = {
    "icon_d2": "DWD ICON-D2 2 km",
    "icon_eu": "DWD ICON-EU 7 km",
    "icon_global": "DWD ICON globale 11 km",
    "ecmwf_ifs": "ECMWF IFS HRES 9 km",
    "ecmwf_ifs025": "ECMWF IFS 0,25",
    "ecmwf_aifs025_single": "ECMWF AIFS 0,25",
    "gfs_global": "NOAA GFS 0,11/0,25",
    "arpege_europe": "Meteo-France ARPEGE Europa 0,1",
    "arpege_world": "Meteo-France ARPEGE mondo 0,25",
    "meteofrance_arome_france": "Meteo-France AROME Francia",
    "chmi_aladin_central_europe_2km": "CHMI ALADIN Europa centrale 2,3 km",
    "chmi_seamless": "CHMI (combinato)",
    "geosphere_arome_austria": "GeoSphere AROME Austria 2,5 km",
    "knmi_harmonie_arome_europe": "KNMI Harmonie Europa 5,5 km",
    "dmi_harmonie_arome_europe": "DMI Harmonie Europa 2 km",
    "metno_seamless": "MET Norway",
    "ukmo_global_deterministic_10km": "UK Met Office globale 10 km",
    "gem_global": "Canada GEM globale 15 km",
    "jma_gsm": "Giappone GSM",
    "italia_meteo_arpae_icon_2i": "ICON-2I Italia",
}

# Scelti dopo la ricognizione del 16/11/2026 (vedi PROGETTO.md). L'archivio salva questi.
SCELTI = [
    "chmi_aladin_central_europe_2km", "dmi_harmonie_arome_europe", "knmi_harmonie_arome_europe",
    "icon_eu", "ecmwf_ifs", "ecmwf_ifs025", "arpege_europe", "ukmo_global_deterministic_10km",
    "gfs_global", "icon_global", "ecmwf_aifs025_single", "gem_global",
]

ORARIE = [
    "temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation", "rain",
    "snowfall", "snow_depth", "freezing_level_height", "weather_code", "cloud_cover",
    "cloud_cover_low", "visibility", "pressure_msl", "surface_pressure",
    "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "shortwave_radiation", "cape",
    "temperature_925hPa", "temperature_850hPa", "temperature_700hPa",
    "wind_speed_850hPa", "wind_direction_850hPa", "geopotential_height_850hPa",
]


def url_previsione(lat, lon, modello, variabili=None, giorni=7, base="https://api.open-meteo.com/v1/forecast", extra=""):
    v = ",".join(variabili or ORARIE)
    # elevation=nan: valori grezzi della cella del modello, senza la correzione di quota di Open-Meteo
    return (f"{base}?latitude={lat}&longitude={lon}&hourly={v}&models={modello}"
            f"&forecast_days={giorni}&timezone=UTC&wind_speed_unit=ms&elevation=nan&cell_selection=nearest{extra}")

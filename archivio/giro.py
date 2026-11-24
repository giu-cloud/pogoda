"""Giro d'archivio. A ogni giro: osservazioni IMGW entro 60 km.
Ai giri delle 02, 08, 14, 20 UTC (o a mano): anche le previsioni di tutti i modelli sul punto.
Salva file compressi in archivio/dati/AAAA-MM/. Solo libreria standard: nessuna installazione."""
import datetime as dt, gzip, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from comune.base import casa, scarica_json, km, pulisci, SCELTI, url_previsione, SUF

RAGGIO_KM = 60
QUI = os.path.dirname(__file__)


def salva(percorso, oggetto):
    os.makedirs(os.path.dirname(percorso), exist_ok=True)
    with gzip.open(percorso, "wt", encoding="utf-8") as f:
        json.dump(oggetto, f, ensure_ascii=False, separators=(",", ":"))


def osservazioni(lat, lon):
    fuori = {"stazioni": [], "sinottiche": [], "errori": []}
    stato, dati = scarica_json("https://danepubliczne.imgw.pl/api/data/meteo")
    if stato == 200 and isinstance(dati, list):
        for s in dati:
            try:
                d = km(lat, lon, float(s["lat"]), float(s["lon"]))
            except Exception:
                continue
            if d <= RAGGIO_KM:
                s["distanza_km"] = round(d)
                fuori["stazioni"].append(s)
    else:
        fuori["errori"].append(f"meteo: {dati}")
    stato, dati = scarica_json("https://danepubliczne.imgw.pl/api/data/synop")
    if stato == 200 and isinstance(dati, list):
        nomi = ("Nowy Sącz", "Krosno", "Tarnów", "Lesko", "Zakopane", "Kasprowy Wierch", "Rzeszów", "Przemyśl", "Sanok")
        fuori["sinottiche"] = [s for s in dati if s.get("stacja") in nomi]
    else:
        fuori["errori"].append(f"synop: {dati}")
    return fuori


def previsioni(lat, lon):
    elenco = SCELTI
    fuori = {}
    def leggi(modello):
        stato, dati = scarica_json(url_previsione(lat, lon, modello), timeout=30, tentativi=3)
        if stato == 200 and isinstance(dati, dict) and "hourly" in dati:
            # tolgo le coordinate: nel file resta solo la quota della cella
            return {"quota_cella": dati.get("elevation"), "hourly": dati["hourly"]}
        return {"errore": pulisci(dati, lat, lon)[:300]}
    for modello in elenco:
        fuori[modello] = leggi(modello)
    # secondo passaggio per i modelli caduti per un guasto di rete passeggero
    for modello in [m for m, v in fuori.items() if "errore" in v and "HTTP 400" not in v["errore"]]:
        fuori[modello] = leggi(modello)
    return fuori


def main():
    lat, lon, _ = casa()
    ora = dt.datetime.now(dt.timezone.utc)
    cartella = os.path.join(QUI, "dati" + SUF, ora.strftime("%Y-%m"))
    marca = ora.strftime("%Y%m%d_%H%M")
    oss = osservazioni(lat, lon)
    salva(os.path.join(cartella, f"oss_{marca}.json.gz"), {"letto_utc": ora.isoformat(), **oss})
    print(f"osservazioni: {len(oss['stazioni'])} stazioni, {len(oss['sinottiche'])} sinottiche, errori {len(oss['errori'])}")
    forza = os.environ.get("FORZA_PREVISIONI") == "1"
    # GitHub fa partire i giri anche 45 minuti dopo l'orario: non mi fido dell'ora, guardo l'eta' dell'ultimo file
    import glob
    vecchi = sorted(os.path.basename(f) for f in glob.glob(os.path.join(QUI, "dati" + SUF, "*", "prev_*.json.gz")))
    eta_h = 99.0
    if vecchi:
        ultimo = dt.datetime.strptime(vecchi[-1][5:18], "%Y%m%d_%H%M").replace(tzinfo=dt.timezone.utc)
        eta_h = (ora - ultimo).total_seconds() / 3600
    if forza or eta_h >= 5.0:
        prev = previsioni(lat, lon)
        salva(os.path.join(cartella, f"prev_{marca}.json.gz"), {"letto_utc": ora.isoformat(), "modelli": prev})
        buoni = [m for m, v in prev.items() if "hourly" in v]
        print(f"previsioni: {len(buoni)} modelli su {len(prev)}")
    if oss["errori"] and not oss["stazioni"]:
        sys.exit("Nessuna osservazione letta")


if __name__ == "__main__":
    main()

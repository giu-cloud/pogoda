"""Campi meteo sul quadrato della mappa: una griglia G x G di punti dal modello piu' fine che copre la zona.
Scrive mappa/uscita/campi.json (senza coordinate). Gira solo quando girano le previsioni."""
import datetime as dt, json, math, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from comune.base import casa, scarica_json, pulisci, SUF
from mappa.geo import griglia, G, LATI

QUI = os.path.dirname(__file__)
MODELLI = ["chmi_aladin_central_europe_2km", "icon_eu"]
VAR = ["temperature_2m", "dew_point_2m", "precipitation", "cloud_cover_low", "cloud_cover",
       "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m",
       "pressure_msl", "cape", "shortwave_radiation", "visibility", "temperature_850hPa"]
# Open-Meteo conta ogni punto come una richiesta (di piu' oltre 10 variabili), con un tetto di 600 al minuto:
# qui si tiene il conto e si aspetta quando serve.
PESO = math.ceil(len(VAR) / 10)
SPESI = []


def attendi(n):
    while True:
        ora = time.time()
        SPESI[:] = [(t, k) for t, k in SPESI if ora - t < 62]
        if sum(k for _, k in SPESI) + n <= 480:
            SPESI.append((ora, n))
            return
        time.sleep(5)
ORE = 48


def leggi(punti, modello):
    tutti = []
    for i in range(0, len(punti), 85):
        p = punti[i:i + 85]
        base = ("https://api.open-meteo.com/v1/forecast?latitude=" + ",".join(f"{a:.4f}" for a, _ in p)
                + "&longitude=" + ",".join(f"{b:.4f}" for _, b in p) + "&hourly=" + ",".join(VAR)
                + f"&models={modello}&forecast_days=3&timezone=UTC&wind_speed_unit=kmh&cell_selection=nearest")
        d = None
        attendi(len(p) * PESO)
        for extra in ("&elevation=nan", "&elevation=" + ",".join(["nan"] * len(p)), ""):
            stato, d = scarica_json(base + extra, timeout=60)
            if stato == 429:
                time.sleep(62)
                stato, d = scarica_json(base + extra, timeout=60)
            if stato == 200 and isinstance(d, (list, dict)):
                break
        else:
            raise RuntimeError(str(d)[:200])
        d = d if isinstance(d, list) else [d]
        if len(d) != len(p):
            raise RuntimeError(f"attesi {len(p)} punti, arrivati {len(d)}")
        tutti += d
    return tutti


def pendenza(z, t):
    """Gradi per km dalla relazione temperatura-quota tra i punti della griglia (minimi quadrati)."""
    c = [(a, b) for a, b in zip(z, t) if a is not None and b is not None]
    if len(c) < 20:
        return -6.5
    mz, mt = sum(a for a, _ in c) / len(c), sum(b for _, b in c) / len(c)
    v = sum((a - mz) ** 2 for a, _ in c)
    if v < len(c) * 60 ** 2:  # quote troppo simili: niente stima
        return -6.5
    g = sum((a - mz) * (b - mt) for a, b in c) / v * 1000
    return max(-9.8, min(8.0, g))


def main():
    ora = dt.datetime.now(dt.timezone.utc)
    # stessa regola del giro d'archivio: i campi si rileggono quando il giro ha appena letto le previsioni
    import glob
    v = sorted(os.path.basename(f) for f in glob.glob(os.path.join(QUI, "..", "archivio", "dati" + SUF, "*", "prev_*.json.gz")))
    fresco = bool(v) and (ora - dt.datetime.strptime(v[-1][5:18], "%Y%m%d_%H%M").replace(tzinfo=dt.timezone.utc)).total_seconds() < 900
    if os.environ.get("FORZA_PREVISIONI") != "1" and not fresco:
        print("campi: non e' un giro di previsioni")
        return
    lat, lon, _ = casa()
    for lato in LATI:
        campo(lat, lon, lato, ora)


def campo(lat, lon, lato, ora):
    punti = griglia(lat, lon, lato)
    dati, usato = None, None
    for m in MODELLI:
        try:
            dati = leggi(punti, m)
            # il modello deve coprire tutta la carta, non solo il centro
            if sum(1 for x in dati if x["hourly"]["temperature_2m"][0] is not None) >= 0.97 * len(dati):
                usato = m
                break
        except Exception as ex:
            print("campi:", m, pulisci(f"{type(ex).__name__}: {ex}", lat, lon)[:300])
    if not usato:
        print(f"campi {lato} km: nessun modello letto, tengo il file precedente")
        return
    tempi = dati[0]["hourly"]["time"]
    t0 = ora.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M")
    i0 = tempi.index(t0) if t0 in tempi else 0
    n = min(ORE, len(tempi) - i0)
    z = [x.get("elevation") for x in dati]
    col = lambda k, h, f=1: [None if x["hourly"][k][i0 + h] is None else round(x["hourly"][k][i0 + h] * f) for x in dati]
    out = {"modello": usato, "t0": tempi[i0], "ore": n, "G": G, "z": [None if a is None else round(a) for a in z],
           "T": [], "Td": [], "pr": [], "low": [], "nuv": [], "ws": [], "wd": [], "wg": [], "gamma": [],
           "p": [], "cape": [], "sw": [], "vis": [], "T850": []}
    for h in range(n):
        out["T"].append(col("temperature_2m", h, 10)); out["Td"].append(col("dew_point_2m", h, 10))
        out["pr"].append(col("precipitation", h, 10)); out["low"].append(col("cloud_cover_low", h))
        out["nuv"].append(col("cloud_cover", h)); out["ws"].append(col("wind_speed_10m", h))
        out["wd"].append(col("wind_direction_10m", h)); out["wg"].append(col("wind_gusts_10m", h))
        out["p"].append(col("pressure_msl", h, 10)); out["cape"].append(col("cape", h))
        out["sw"].append(col("shortwave_radiation", h)); out["vis"].append(col("visibility", h, 0.01))
        out["T850"].append(col("temperature_850hPa", h, 10))
        out["gamma"].append(round(pendenza(z, [x["hourly"]["temperature_2m"][i0 + h] for x in dati]), 2))
    os.makedirs(os.path.join(QUI, "uscita" + SUF), exist_ok=True)
    json.dump(out, open(os.path.join(QUI, "uscita" + SUF, f"campi_{lato}.json"), "w"), separators=(",", ":"))
    print(f"campi {lato} km: {usato}, {n} ore, quote celle {min(a for a in z if a is not None):.0f}-{max(a for a in z if a is not None):.0f} m, gradienti {min(out['gamma'])}..{max(out['gamma'])}")


if __name__ == "__main__":
    main()

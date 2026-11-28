"""Onde per la carta di Pistrice, prese da un modello del mare via Open-Meteo Marine (CC BY 4.0) senza rielaborarle:
altezza significativa, direzione di provenienza e periodo, su una griglia di circa 2,5 km sul riquadro.
I punti senza dato (terra, o celle del modello di onde troppo vicine alla costa) prendono il valore del punto di mare
piu' vicino: sotto costa quindi niente rifrazione ne' ridosso, solo il dato del largo. E' scritto nella pagina."""
import json, os, sys, time, urllib.parse
import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
from lens.base import scarica_json  # noqa: E402

MODELLI = ["meteofrance_wave", "ewam", "ecmwf_wam025", "best_match"]
NOMI = {"meteofrance_wave": "MFWAM (Météo-France)", "ewam": "EWAM (DWD)", "ecmwf_wam025": "WAM (ECMWF)", "best_match": "Open-Meteo Marine"}
VAR = ["wave_height", "wave_direction", "wave_period"]


def leggi(interno, tempi, passo=0.025):
    s, n, o, e = interno
    lat = np.arange(n, s - 1e-9, -passo)
    lon = np.arange(o, e + 1e-9, passo)
    LA, LO = np.meshgrid(lat, lon, indexing="ij")
    pts = list(zip(LA.ravel().round(4), LO.ravel().round(4)))
    for m in MODELLI:
        righe = []
        ok = True
        for i in range(0, len(pts), 100):
            blocco = pts[i:i + 100]
            q = {"latitude": ",".join(str(p[0]) for p in blocco), "longitude": ",".join(str(p[1]) for p in blocco),
                 "hourly": ",".join(VAR), "timezone": "GMT", "forecast_days": 3, "past_days": 1}
            if m != "best_match":
                q["models"] = m
            stato, d = scarica_json("https://marine-api.open-meteo.com/v1/marine?" + urllib.parse.urlencode(q), timeout=90)
            if stato != 200 or d is None:
                print("onde:", m, "non letto:", stato, str(d)[:150])
                ok = False
                break
            righe += d if isinstance(d, list) else [d]
            time.sleep(1)
        if not ok:
            continue
        t = righe[0]["hourly"]["time"]
        idx = [t.index(x) if x in t else None for x in tempi]
        H = np.full((len(tempi), len(pts)), np.nan); Dd = H.copy(); T = H.copy()
        for k, r in enumerate(righe):
            hh = r.get("hourly", {})
            for j, ix in enumerate(idx):
                if ix is None:
                    continue
                a, b, c = (hh.get(v, [None] * (ix + 1))[ix] for v in VAR)
                if a is not None and b is not None:
                    H[j, k], Dd[j, k], T[j, k] = a, b, (c if c is not None else np.nan)
        validi = np.isfinite(H).any(axis=0)
        if validi.sum() < 10:
            print("onde:", m, "troppo pochi punti di mare:", int(validi.sum()))
            continue
        # i punti senza dato prendono il punto di mare piu' vicino
        from scipy.ndimage import distance_transform_edt
        g = validi.reshape(LA.shape)
        _, (ii, jj) = distance_transform_edt(~g, return_indices=True)
        vicino = (ii * LA.shape[1] + jj).ravel()
        H, Dd, T = H[:, vicino], Dd[:, vicino], T[:, vicino]
        print(f"onde: {m}, {int(validi.sum())} punti di mare su {len(pts)}")
        r1 = lambda a, f: [[None if not np.isfinite(x) else round(float(x), f) for x in riga] for riga in a]
        return {"modello": NOMI.get(m, m), "gy": int(LA.shape[0]), "gx": int(LA.shape[1]),
                "box": [float(lat[-1]), float(lat[0]), float(lon[0]), float(lon[-1])],
                "h": r1(H, 2), "d": r1(Dd, 0), "p": r1(T, 1)}
    print("onde: nessun modello letto")
    return None

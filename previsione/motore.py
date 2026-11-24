"""Motore v0. Dalle previsioni grezze dei modelli (ultimo file prev_*) e dalle osservazioni
(ultimo file oss_*) ricava la previsione alla quota della casa.
Che cosa fa, in ordine:
 1. temperatura: porta ogni modello dalla quota della sua cella alla quota della casa lungo il
    gradiente che quel modello ha tra il suolo e 850 hPa (cosi' un'inversione notturna non viene
    trattata come aria libera); senza livelli in quota usa -6,5 gradi/km;
 2. umidita', bulbo umido, fase della precipitazione (pioggia, mista, neve) alla quota della casa;
 3. nube sulla casa: aria satura alla quota della casa, oppure base delle nubi (livello di
    condensazione) sotto la casa con aria rimescolata e nubi basse previste;
 4. mediana tra i modelli e forchetta 10-90%.
Non c'e' ancora correzione statistica: e' la base su cui misurare i miglioramenti."""
import datetime as dt, glob, gzip, json, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from comune.base import SUF

QUI = os.path.dirname(__file__)
DATI = os.path.join(QUI, "..", "archivio", "dati" + SUF)
ORE = 144


def ultimo(prefisso):
    f = sorted(glob.glob(os.path.join(DATI, "*", prefisso + "_*.json.gz")), key=os.path.basename)
    if not f:
        return None
    with gzip.open(f[-1], "rt", encoding="utf-8") as h:
        return json.load(h)


def num(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def quant(v, p):
    v = sorted(x for x in v if x is not None)
    if not v:
        return None
    if len(v) == 1:
        return v[0]
    k = (len(v) - 1) * p
    i = int(k)
    j = min(i + 1, len(v) - 1)
    return v[i] + (v[j] - v[i]) * (k - i)


def rugiada(t, ur):
    if t is None or ur is None or ur <= 0:
        return None
    g = math.log(min(ur, 100.0) / 100.0) + 17.625 * t / (243.04 + t)
    return 243.04 * g / (17.625 - g)


def umidita(t, td):
    if t is None or td is None:
        return None
    e = lambda x: math.exp(17.625 * x / (243.04 + x))
    return max(1.0, min(100.0, 100.0 * e(td) / e(t)))


def bulbo_umido(t, ur):
    """Formula di Stull (2011), valida per le condizioni ordinarie al suolo."""
    if t is None or ur is None:
        return None
    ur = max(5.0, min(99.0, ur))
    return (t * math.atan(0.151977 * math.sqrt(ur + 8.313659)) + math.atan(t + ur) - math.atan(ur - 1.676331)
            + 0.00391838 * ur ** 1.5 * math.atan(0.023101 * ur) - 4.686035)


def r1(x, n=1):
    return None if x is None else round(x, n)


def per_modello(nome, m, quota):
    """Ritorna {ora_iso: valori alla quota della casa} per un modello."""
    h = m.get("hourly") or {}
    zc = num(m.get("quota_cella"))
    tempi = h.get("time") or []
    g = lambda k, i: num((h.get(k) or [None] * len(tempi))[i]) if i < len(h.get(k) or []) else None
    fuori = {}
    for i, t in enumerate(tempi):
        tc = g("temperature_2m", i)
        if tc is None or zc is None:
            continue
        tdc = g("dew_point_2m", i)
        if tdc is None:
            tdc = rugiada(tc, g("relative_humidity_2m", i))
        dz = quota - zc
        t850, z850 = g("temperature_850hPa", i), g("geopotential_height_850hPa", i)
        if t850 is not None and z850 is not None and z850 - zc > 300 and z850 - quota > 100:
            grad = (t850 - tc) / (z850 - zc)  # gradi per metro, del modello stesso
            grad = max(-0.0098, min(0.010, grad))
        else:
            grad = -0.0065
        th = tc + grad * dz
        tdh = None if tdc is None else min(th, tdc - 0.002 * dz)
        urh = umidita(th, tdh)
        tw = bulbo_umido(th, urh)
        stabile = dz > 0 and grad > -0.002  # aria poco rimescolata: la valle non dice che cosa c'e' in cresta
        base = None if tdc is None else zc + 125.0 * max(0.0, tc - tdc)
        basse = g("cloud_cover_low", i)
        vis = g("visibility", i)
        wc, cape = g("weather_code", i), g("cape", i)
        nube = False
        if urh is not None and urh >= 96.0:
            nube = True
        elif base is not None and not stabile and base <= quota + 25 and (basse is None or basse >= 50):
            nube = True
        # nebbia nei fondovalle sotto la casa: aria ferma e stabile, quasi satura gia' alla quota della cella.
        # I fondovalle veri sono piu' bassi e piu' freddi di qualunque cella: e' un indizio, non una misura.
        calma = g("wind_speed_10m", i)
        valle = bool(grad > -0.003 and tdc is not None and tc - tdc <= 1.5 and (calma is None or calma <= 3.0) and not nube)
        pr = g("precipitation", i)
        fase = None
        if tw is not None:
            fase = "neve" if tw <= 0.5 else ("mista" if tw <= 1.5 else "pioggia")
        fuori[t] = {
            "T": th, "Td": tdh, "UR": urh, "Tw": tw, "grad": grad * 1000, "nube": nube, "valle": valle,
            "base": base, "pr": pr, "fase": fase, "vento": g("wind_speed_10m", i), "raffica": g("wind_gusts_10m", i),
            "dir": g("wind_direction_10m", i), "basse": basse, "zero": g("freezing_level_height", i),
            "nuv": g("cloud_cover", i), "vis": vis, "Tgrezza": tc,
            "temporale": bool((wc is not None and wc >= 95) or (cape is not None and cape >= 800 and (pr or 0) >= 0.5)),
        }
    return fuori


def adesso(oss, quota):
    """Che cosa dicono adesso le stazioni vere intorno alla casa. Le stazioni di riferimento si scelgono da sole:
    la piu' vicina con temperatura e umidita' per la base delle nubi, la piu' bassa e la piu' alta per il gradiente."""
    if not oss:
        return None
    righe = []
    for s in oss.get("stazioni", []):
        t, ur = num(s.get("temperatura_powietrza")), num(s.get("wilgotnosc_wzgledna"))
        q, d = num(s.get("wysokosc_npm")), num(s.get("distanza_km"))
        if t is None or q is None or d is None or d > 45:
            continue
        v = num(s.get("wiatr_srednia_predkosc"))
        righe.append({"nome": str(s.get("nazwa_stacji", "")).title(), "quota": q, "km": d,
                      "T": t, "UR": ur, "Td": r1(rugiada(t, ur)), "vento_kmh": r1(None if v is None else v * 3.6, 0),
                      "dir": num(s.get("wiatr_kierunek")), "ora": s.get("temperatura_powietrza_data")})
    if not righe:
        return None
    righe.sort(key=lambda r: r["km"])
    fuori = {"stazioni": righe[:9], "letto_utc": oss.get("letto_utc")}
    vicine = [r for r in righe if abs(r["quota"] - quota) <= 80 and r["km"] <= 35]
    if vicine:
        # mediana: una stazione fuori dal coro (favonio, sensore) non sposta la stima
        fuori["T_stima"] = r1(quant([r["T"] - 0.0065 * (quota - r["quota"]) for r in vicine], 0.5))
        fuori["T_stima_da"] = [r["nome"] for r in vicine]
    u = next((r for r in righe if r["Td"] is not None and r["km"] <= 25), None)
    if u:
        fuori["base_nubi"] = round(u["quota"] + 125.0 * max(0.0, u["T"] - u["Td"]), -1)
        fuori["base_da"] = {"nome": u["nome"], "quota": u["quota"], "UR": u["UR"]}
    basso, alto = min(righe, key=lambda r: r["quota"]), max(righe, key=lambda r: r["quota"])
    if alto["quota"] - basso["quota"] >= 300:
        fuori["grad_oss"] = r1((alto["T"] - basso["T"]) / (alto["quota"] - basso["quota"]) * 1000)
        fuori["grad_da"] = [basso["nome"], basso["quota"], alto["nome"], alto["quota"]]
        fuori["inversione"] = alto["T"] > basso["T"] - 1.0
    # nebbia di fondovalle adesso: stazione piu' bassa della casa quasi satura, con aria ferma o inversione
    if u and u["quota"] < quota - 60 and u["UR"] is not None and u["UR"] >= 97 and fuori.get("grad_oss", -9) > -3.5:
        fuori["nebbia_valle"] = True
    return fuori


def calcola(prev, oss, quota, ora=None):
    ora = ora or dt.datetime.now(dt.timezone.utc)
    inizio = ora.replace(minute=0, second=0, microsecond=0)
    modelli = {n: per_modello(n, m, quota) for n, m in (prev or {}).get("modelli", {}).items() if "hourly" in m}
    ore = []
    for k in range(ORE):
        t = inizio + dt.timedelta(hours=k)
        chiave = t.strftime("%Y-%m-%dT%H:%M")
        v = [m[chiave] for m in modelli.values() if chiave in m]
        if len(v) < 3:
            continue
        c = lambda nome: [x[nome] for x in v if x[nome] is not None]
        tm = quant(c("T"), 0.5)
        ur = quant(c("UR"), 0.5)
        tw = quant(c("Tw"), 0.5)
        pr = quant(c("pr"), 0.5) or 0.0
        fase = None if tw is None else ("neve" if tw <= 0.5 else ("mista" if tw <= 1.5 else "pioggia"))
        zero = quant(c("zero"), 0.5)
        ore.append({
            "t": chiave, "n": len(v), "T": r1(tm), "T10": r1(quant(c("T"), 0.1)), "T90": r1(quant(c("T"), 0.9)),
            "UR": r1(ur, 0), "pr": r1(pr, 1), "pr90": r1(quant(c("pr"), 0.9), 1), "fase": fase,
            "neve_cm": r1(pr if fase == "neve" else (pr * 0.5 if fase == "mista" else 0.0), 1),
            "p_neve": r1(sum(1 for x in v if x["fase"] == "neve") / len(v), 2),
            "vento": r1(None if not c("vento") else quant(c("vento"), 0.5) * 3.6, 0),
            "raffica": r1(None if not c("raffica") else quant(c("raffica"), 0.5) * 3.6, 0),
            "raffica90": r1(None if not c("raffica") else quant(c("raffica"), 0.9) * 3.6, 0),
            "dir": r1(quant(c("dir"), 0.5), 0),
            "nube": r1(sum(1 for x in v if x["nube"]) / len(v), 2),
            "valle": r1(sum(1 for x in v if x["valle"]) / len(v), 2),
            "nuv": r1(quant(c("nuv"), 0.5), 0), "zero": r1(zero, -1),
            "quota_neve": r1(None if zero is None else max(0.0, zero - 300.0), -2),
            "gelicidio": bool(tm is not None and tm <= 0.0 and pr >= 0.2 and fase == "pioggia"),
            "temporale": r1(sum(1 for x in v if x["temporale"]) / len(v), 2),
        })
    # ghiaccio sulle strade: intorno a zero (anche solo per i modelli piu' freddi) con fondo bagnato o aria satura
    for i, o in enumerate(ore):
        bagnato = sum((x["pr"] or 0) for x in ore[max(0, i - 6):i + 1]) >= 0.3 or (o["UR"] or 0) >= 95 or (o["nube"] or 0) >= 0.5
        freddo = (o["T"] is not None and o["T"] <= 0.5) or (o["T10"] is not None and o["T10"] <= -0.5)
        o["ghiaccio"] = bool(bagnato and freddo)
    return {"generato_utc": ora.isoformat(timespec="minutes"), "previsioni_lette_utc": (prev or {}).get("letto_utc"),
            "quota": quota, "modelli": sorted(modelli), "ore": ore, "adesso": adesso(oss, quota),
            "quote_celle": {n: m.get("quota_cella") for n, m in (prev or {}).get("modelli", {}).items() if "hourly" in m}}


def main():
    import base64
    from comune.base import casa
    lat, lon, quota = casa()
    from mappa.geo import riquadro, LATI
    radice = os.path.join(QUI, "..", "mappa")
    if quota is None:  # senza quota dichiarata uso quella del rilievo al centro della carta
        try:
            quota = float(json.load(open(os.path.join(radice, "base" + SUF, f"base_{LATI[-1]}.json")))["quota_dem_centro"])
        except Exception:
            print("Quota della casa non nota (ne' Secret ne' carta di base): salto.")
            return
    prev, oss = ultimo("prev"), ultimo("oss")
    if not prev:
        print("Nessun file di previsioni ancora: salto.")
        return
    ris = calcola(prev, oss, quota)
    # posizione delle stazioni sulle carte, come frazioni del quadrato (niente coordinate della casa nei file)
    ris["mappa_stazioni"] = {}
    mappa = {}
    for lato in LATI:
        s_, n_, o_, e_ = riquadro(lat, lon, lato)
        st = []
        for x in (oss or {}).get("stazioni", []):
            try:
                fx, fy = (float(x["lon"]) - o_) / (e_ - o_), (n_ - float(x["lat"])) / (n_ - s_)
            except (TypeError, ValueError, KeyError):
                continue
            if 0 < fx < 1 and 0 < fy < 1:
                st.append({"n": str(x.get("nazwa_stacji", "")).title(), "x": round(fx, 4), "y": round(fy, 4),
                           "T": num(x.get("temperatura_powietrza")), "q": num(x.get("wysokosc_npm"))})
        ris["mappa_stazioni"][str(lato)] = st
        try:
            mappa[str(lato)] = {"base": json.load(open(os.path.join(radice, "base" + SUF, f"base_{lato}.json"))),
                                "campi": json.load(open(os.path.join(radice, "uscita" + SUF, f"campi_{lato}.json"))),
                                "jpg": base64.b64encode(open(os.path.join(radice, "base" + SUF, f"base_{lato}.jpg"), "rb").read()).decode()}
        except Exception as ex:
            print(f"mappa {lato} km non disponibile:", type(ex).__name__, ex)
    mappa = mappa or None
    uscita = os.path.join(QUI, "uscita" + SUF)
    os.makedirs(uscita, exist_ok=True)
    json.dump(ris, open(os.path.join(uscita, "previsione.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    from previsione.pagina import pagina
    open(os.path.join(uscita, "pagina.html"), "w", encoding="utf-8").write(pagina(ris, mappa))
    print(f"previsione{SUF}: {len(ris['ore'])} ore, {len(ris['modelli'])} modelli, mappe {sorted(mappa) if mappa else 'nessuna'}")


if __name__ == "__main__":
    main()

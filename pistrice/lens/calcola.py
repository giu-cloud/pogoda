"""Lens: vento ad alta definizione su un riquadro scelto, partendo da un modello meteo.

Metodo (descritto per intero in METODO.md):
  1. rilievo vero (Copernicus DEM 30 m) e rugosita' (ESA WorldCover) su una griglia fine, regolare in lat/lon;
  2. campo di partenza 3D dal modello: vento a 10 m (celle di mare per il mare, di terra per la terra) raccordato
     al profilo verticale del modello su 8 livelli di pressione, punto per punto;
  3. stabilita' a due strati (sotto e sopra la cima dei rilievi) dal profilo di temperatura del modello;
  4. aggiustamento a conservazione di massa in 3D (Sherman 1978) con multigrid algebrico;
  5. vento a 10 m dal suolo con il profilo logaritmico della rugosita' locale;
  6. ridosso sottovento ai rilievi e frenata della costa (strato limite interno), il piu' forte dei due;
  7. raffiche dalla turbolenza locale, tarate sul rapporto raffica/vento del modello in mare aperto.
Uscite: pagina HTML da scorrere ora per ora e GRIB2 (u, v, raffica a 10 m) da aprire in Shift.

Parametri (variabili d'ambiente, tutte facoltative; senza, calcola i golfi di Palermo e Mondello):
  LENS_AREA     "S,N,O,E" del riquadro che interessa (il margine di calcolo si aggiunge da solo)
  LENS_NOME     titolo della pagina
  LENS_MODELLO  modello di partenza (nome Open-Meteo); di default ICON-2I, poi ICON-EU
  LENS_ORE      ore da calcolare (default 15)   LENS_DA  prima ora, da adesso (default 0)
  LENS_INIZIO   prima ora in UTC, "2026-11-21T06:00" (vince su LENS_DA): e' quella che manda Shift
  LENS_DX       maglia in metri (default: la piu' fitta che sta nella memoria, non sotto 150 m)
  LENS_ID       nome del calcolo: il GRIB si chiama lens_<ID>.grb2 (senza, lens.grb2)
  LENS_PAGINA   "1" per fare anche la pagina HTML (carta di base e nomi da OpenStreetMap): Shift non la chiede
  LENS_RILIEVO, LENS_RIDOSSO, LENS_RIDOSSO_S, LENS_COSTA: quanto pesano i pezzi di Lens (0.54, banco col radar dei
                Sentinel-1, routing/atlante_costa_risultati.md); i valori di prima sono 1, 0.65, 3, 1"""
import base64, datetime as dt, gzip, io, json, math, os, sys, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lens.base import scarica_json, UA
from lens.solutore import livelli, aggiusta, al_suolo, scia, costa, raffiche

QUI = os.path.dirname(__file__)
PAGINA = os.environ.get("LENS_PAGINA") == "1"
# 0.54: il radar dei Sentinel-1 (10 aree, 2024-26) non vede in media né la frenata del rilievo né il ridosso lungo di
# Lens; restano più leggeri, come nell'app (LensAtlas: shift.lens.terrain, wake, sfacMax, coast).
# Lens 0.57 (Giano, 25/11 sera): torna la forza del primo Lens (rilievo 1, ridosso 0,65, allungamento 3, costa 1), a
# 100 m. LENS_FORZA e' la manopola (1 = primo Lens, 0 = la 0.54), come LensAtlas.RELIEF del motore di Shift. Lens 2 sopra
# diventa relativo a Lens (radar.relativo_a_lens), per non contare due volte le ombre che il radar vede.
FORZA = min(1.0, max(0.0, float(os.environ.get("LENS_FORZA") or 1.0)))
RILIEVO = float(os.environ.get("LENS_RILIEVO") or FORZA)
RIDOSSO = float(os.environ.get("LENS_RIDOSSO") or (0.2 + 0.45 * FORZA))
RIDOSSO_S = float(os.environ.get("LENS_RIDOSSO_S") or (1.0 + 2.0 * FORZA))
COSTA = float(os.environ.get("LENS_COSTA") or FORZA)
# Lens 0.56 (Giano, 25/11): la direzione del rilievo pieno con la forza della 0.54. Il radar non misura la direzione; le
# stazioni sulla costa (Messina, Reggio, Mentone, Cap Corse) dicono che la rotazione del rilievo la migliora di 7-13°
# (giu-cloud/lens, banco/risultati/cfd_25_11.md). La rotazione si applica alla fine, quindi forza e raffica non cambiano.
# 0 = come la 0.54, 1 = tutta (come LensAtlas.TERRAIN_DIR_WEIGHT del motore di Shift).
DIR_RIL = float(os.environ.get("LENS_DIR_RILIEVO") or 1.0)
ID = "".join(c for c in (os.environ.get("LENS_ID") or "") if c.isalnum() or c in "-_")[:80]
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("AWS_NO_SIGN_REQUEST", "YES")

PALERMO = {"area": (37.945, 38.345, 13.108, 13.612), "nome": "Pistrice Sailing Weather Lab", "casa": None,
           "viste": {"Tutto": None, "Due golfi": (38.060, 38.250, 13.250, 13.560), "Mondello": (38.170, 38.240, 13.272, 13.372),
                     "Golfo di Palermo": (38.085, 38.200, 13.340, 13.500),
                     # Pietro's Place (il suo bar) al centro, stessa misura della vista del golfo di Palermo
                     "Pietro's Place": (38.115695 - 0.0575, 38.115695 + 0.0575, 13.364716 - 0.08, 13.364716 + 0.08)},
           "sempre": ("Cuccio", "Grifone", "Catalfano", "Pellegrino", "Gallo", "Zafferano")}
MAX_COLONNE = 100000         # colonne di calcolo che stanno nei 7 GB della macchina di GitHub (misurato: 6 milioni di celle, 4,8 GB)
RISOLUZIONE_KM = {"ecmwf_ifs025": 25.0, "italia_meteo_arpae_icon_2i": 2.2, "meteofrance_arome_france": 1.3, "meteofrance_arome_france_hd": 1.5,
                  "icon_eu": 7.0, "icon_d2": 2.2, "ecmwf_ifs": 9.0, "ecmwf_ifs025": 25.0, "gfs_global": 13.0, "arpege_europe": 11.0}
NOMI_MODELLI = {"youmeteo": "youmeteo a 5,5 km", "ecmwf_ifs025": "ECMWF a 25 km", "italia_meteo_arpae_icon_2i": "ICON-2I a 2,2 km", "icon_eu": "ICON-EU a 7 km", "ecmwf_ifs": "ECMWF a 9 km",
                "gfs_global": "GFS a 13 km", "arpege_europe": "ARPEGE a 11 km", "meteofrance_arome_france": "AROME a 1,3 km"}
LIVELLI_P = [1000, 975, 950, 925, 900, 850, 800, 700]
PRIORITA = {"city": 0, "town": 1, "cape": 2, "village": 3, "suburb": 4, "quarter": 4}


class Area:
    """Riquadro richiesto, dominio di calcolo (con margine) e griglia fine, regolare in latitudine e longitudine."""
    def __init__(self):
        palermo = not os.environ.get("LENS_AREA")
        if palermo:
            s, n, o, e = PALERMO["area"]
        else:
            s, n, o, e = (float(x) for x in os.environ["LENS_AREA"].split(","))
        self.nome = os.environ.get("LENS_NOME") or (PALERMO["nome"] if palermo else "Vento ad alta definizione")
        self.viste = PALERMO["viste"] if palermo else {"Tutto": None}
        self.sempre = PALERMO["sempre"] if palermo else ()
        lat0 = (s + n) / 2
        self.kml = 111.19 * math.cos(math.radians(lat0))
        larg, alt = (e - o) * self.kml, (n - s) * 111.19
        marg = max(2.5, 0.06 * max(larg, alt))                     # km di margine attorno al riquadro
        self.S, self.N = s - marg / 111.19, n + marg / 111.19
        self.O, self.E = o - marg / self.kml, e + marg / self.kml
        area_m2 = (self.N - self.S) * 111190 * (self.E - self.O) * self.kml * 1000
        dx = float(os.environ.get("LENS_DX") or 0) or max(150.0, math.ceil(math.sqrt(area_m2 / MAX_COLONNE) / 10) * 10)
        self.dx = dx
        self.NY = round((self.N - self.S) * 111190 / dx)
        self.NX = round((self.E - self.O) * self.kml * 1000 / dx)
        self.m = round(marg * 1000 / dx)
        self.interno = (self.S + self.m / self.NY * (self.N - self.S), self.N - self.m / self.NY * (self.N - self.S),
                        self.O + self.m / self.NX * (self.E - self.O), self.E - self.m / self.NX * (self.E - self.O))
        self.kb = max(2, min(5, round(dx / 30)))                     # carta di base a circa 30 m

    def lat_lon_fine(self):
        lat = self.N - (np.arange(self.NY) + 0.5) / self.NY * (self.N - self.S)
        lon = self.O + (np.arange(self.NX) + 0.5) / self.NX * (self.E - self.O)
        return lat, lon


A = Area()


def ns(v):
    return ("N" if v >= 0 else "S") + f"{abs(int(math.floor(v))):02d}"


def eo(v):
    return ("E" if v >= 0 else "W") + f"{abs(int(math.floor(v))):03d}"


def url_dem(la, lo):
    n = f"Copernicus_DSM_COG_10_{ns(la)}_00_{eo(lo)}_00_DEM"
    return f"https://copernicus-dem-30m.s3.amazonaws.com/{n}/{n}.tif"


def url_cov(la, lo):
    return f"https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{ns(la)}{eo(lo)}_Map.tif"


def mosaico(url_di, passo, ricampiona, tipo, bbox, forma):
    import rasterio
    from rasterio.windows import from_bounds
    s, n, o, e = bbox
    ny, nx = forma
    fuori = np.zeros((ny, nx), dtype=tipo)
    la = math.floor(s / passo) * passo
    while la < n:
        lo = math.floor(o / passo) * passo
        while lo < e:
            w1, e1, s1, n1 = max(o, lo), min(e, lo + passo), max(s, la), min(n, la + passo)
            c0, c1 = round((w1 - o) / (e - o) * nx), round((e1 - o) / (e - o) * nx)
            r0, r1 = round((n - n1) / (n - s) * ny), round((n - s1) / (n - s) * ny)
            if c1 > c0 and r1 > r0:
                # un riquadro tutto di mare non esiste nell'archivio (risposta 404): resta a zero, cioe' mare
                for tentativo in range(3):
                    try:
                        with rasterio.open(url_di(la, lo)) as ds:
                            fuori[r0:r1, c0:c1] = ds.read(1, window=from_bounds(w1, s1, e1, n1, ds.transform),
                                                          out_shape=(r1 - r0, c1 - c0), resampling=ricampiona, boundless=True)
                        break
                    except Exception as ex:
                        if "404" in str(ex) or "does not exist" in str(ex):
                            print("riquadro di solo mare:", url_di(la, lo).rsplit("/", 1)[-1])
                            break
                        if tentativo == 2:
                            raise
                        time.sleep(5)
            lo += passo
        la += passo
    return fuori


def carta_base(h, cov, passo, el):
    """La grafica di Shift: tinte per quota da carta scolastica, ombreggiatura da nord-ovest, curve brune
    (ogni 100 m, piu' marcate ogni 500), mare e costa con i colori di Shift, fiumi da OpenStreetMap."""
    from PIL import Image, ImageDraw
    rampa = [(0, (0xD3, 0xE0, 0xB8)), (120, (0xDE, 0xE5, 0xBE)), (300, (0xEA, 0xE3, 0xB6)), (500, (0xE3, 0xCF, 0xA2)),
             (700, (0xD3, 0xB9, 0x8C)), (900, (0xBF, 0x9F, 0x7C)), (1100, (0xAB, 0x8D, 0x73)), (1350, (0xA0, 0x86, 0x70))]
    q = np.array([p[0] for p in rampa], dtype=np.float32)
    rgb = np.stack([np.interp(h, q, [p[1][i] for p in rampa]) for i in range(3)], axis=-1)
    def mescola(maschera, colore, forza):
        rgb[maschera] = rgb[maschera] * (1 - forza) + np.array(colore, np.float32) * forza
    mescola(cov == 10, (126, 164, 110), 0.42)
    mescola(cov == 50, (214, 186, 176), 0.55)
    gy, gx = np.gradient(h, passo)
    dzdx, dzdy = gx * 2.4, -gy * 2.4
    rel = np.clip((0.5 * dzdx - 0.5 * dzdy + 0.7071) / np.sqrt(dzdx ** 2 + dzdy ** 2 + 1.0) / 0.7071, 0.0, 1.45)
    rgb *= np.clip(0.52 + 0.48 * rel, 0.55, 1.16)[..., None]
    inchiostro = np.array((0x7A, 0x5A, 0x3C), np.float32)
    for intervallo, forza in ((100, 0.30), (500, 0.58)):
        liv = np.floor(h / intervallo)
        bordo = np.zeros(liv.shape, dtype=bool)
        bordo[:-1, :] |= liv[:-1, :] != liv[1:, :]
        bordo[:, :-1] |= liv[:, :-1] != liv[:, 1:]
        bordo &= h > 1
        rgb[bordo] = rgb[bordo] * (1 - forza) + inchiostro * forza
    mare = (h <= 0.5) & ((cov == 80) | (cov == 0))
    rgb[mare] = (0xCF, 0xE3, 0xEC)
    costa = np.zeros(mare.shape, dtype=bool)
    costa[:-1, :] |= mare[:-1, :] != mare[1:, :]
    costa[:, :-1] |= mare[:, :-1] != mare[:, 1:]
    costa[1:, :] |= mare[1:, :] != mare[:-1, :]
    costa[:, 1:] |= mare[:, 1:] != mare[:, :-1]
    rgb[costa] = (0x8E, 0xA2, 0xB2)
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    s_, n_, o_, e_ = A.interno
    ny, nx = h.shape
    for x in el:
        if x.get("type") == "way" and x.get("geometry"):
            d.line([((g["lon"] - o_) / (e_ - o_) * nx, (n_ - g["lat"]) / (n_ - s_) * ny) for g in x["geometry"]],
                   fill=(66, 128, 204), width=3, joint="curve")
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=80, method=6)
    return base64.b64encode(buf.getvalue()).decode()




def osm():
    """Fiumi, centri abitati, quartieri, capi e cime da OpenStreetMap (ODbL)."""
    import urllib.parse, urllib.request
    s, n, o, e = A.interno
    b = f"{s},{o},{n},{e}"
    q = (f'[out:json][timeout:90];(node["place"~"^(city|town|village|suburb|quarter)$"]["name"]({b});'
         f'node["natural"~"^(peak|cape|volcano)$"]["name"]({b});node["place"="island"]["name"]({b});way["waterway"="river"]({b}););out geom;')
    import hashlib
    riserva = os.path.join(QUI, "cache", "osm_" + hashlib.sha1(b.encode()).hexdigest()[:12] + ".json")
    for tentativo in range(2):
        for server in ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
                       "https://maps.mail.ru/osm/tools/overpass/api/interpreter", "https://overpass.private.coffee/api/interpreter"):
            try:
                req = urllib.request.Request(server, data=urllib.parse.urlencode({"data": q}).encode(), headers=UA)
                with urllib.request.urlopen(req, timeout=120) as r:
                    el = json.loads(r.read())["elements"]
                os.makedirs(os.path.dirname(riserva), exist_ok=True)
                json.dump(el, open(riserva, "w"), separators=(",", ":"))
                return el
            except Exception as ex:
                print("Overpass", server, type(ex).__name__, str(ex)[:120])
        time.sleep(20)
    if os.path.exists(riserva):
        print("OpenStreetMap non raggiungibile: uso la copia salvata")
        return json.load(open(riserva))
    return []


def luoghi(el):
    """Nomi da scrivere sulla carta, in ordine di importanza; la pagina scarta quelli che si sovrappongono."""
    s_, n_, o_, e_ = A.interno
    fuori = []
    for x in el:
        if x.get("type") != "node":
            continue
        t, la, lo = x.get("tags", {}), x["lat"], x["lon"]
        if not (s_ < la < n_ and o_ < lo < e_):
            continue
        nome = t.get("name")
        fx, fy = round((lo - o_) / (e_ - o_), 4), round((n_ - la) / (n_ - s_), 4)
        if t.get("natural") in ("peak", "volcano"):
            try:
                q = round(float(str(t.get("ele", "")).replace(",", ".").split()[0]))
            except (ValueError, IndexError):
                continue
            pri = 0.5 if any(k in nome for k in A.sempre) else (2 if q >= 900 else 3 if q >= 600 else 5)
            fuori.append([f"{nome} {q}", fx, fy, pri, "p"])
        else:
            tipo = t.get("natural") or t.get("place")
            pri = 0.5 if any(k in nome for k in A.sempre) else (1 if tipo == "island" else PRIORITA.get(tipo, 5))
            fuori.append([nome, fx, fy, pri, "l"])
    return sorted(fuori, key=lambda v: v[3])


def terreno():
    from rasterio.enums import Resampling
    tutto = (A.S, A.N, A.O, A.E)
    h = np.maximum(mosaico(url_dem, 1, Resampling.average, np.float32, tutto, (A.NY, A.NX)), 0.0)
    try:
        c = mosaico(url_cov, 3, Resampling.mode, np.uint8, tutto, (A.NY, A.NX))
    except Exception as ex:
        print("WorldCover non letto:", ex)
        c = np.zeros((A.NY, A.NX), np.uint8)
    mare = (h <= 0.5) & ((c == 80) | (c == 0))
    z0 = np.full(h.shape, 0.10, np.float32)
    for classe, v in {10: 0.6, 20: 0.15, 30: 0.05, 40: 0.08, 50: 0.8, 60: 0.02, 80: 0.0005, 90: 0.05}.items():
        z0[c == classe] = v
    z0[mare] = 0.0005
    if not PAGINA:
        return h.astype(float), z0.astype(float), mare, None, []
    m = A.m
    forma = ((A.NY - 2 * m) * A.kb, (A.NX - 2 * m) * A.kb)
    hb = np.maximum(mosaico(url_dem, 1, Resampling.bilinear, np.float32, A.interno, forma), 0.0)
    try:
        cb = mosaico(url_cov, 3, Resampling.mode, np.uint8, A.interno, forma)
    except Exception:
        cb = np.zeros(forma, np.uint8)
    el = osm()
    return h.astype(float), z0.astype(float), mare, carta_base(hb, cb, A.dx / A.kb, el), luoghi(el)


# ---------------------------------------------------------------- modello di partenza
def griglia_punti(passo_km, massimo):
    """Punti del modello sul dominio di calcolo: passo pari alla risoluzione del modello, ma non piu' di 'massimo' punti."""
    larg, alt = (A.E - A.O) * A.kml, (A.N - A.S) * 111.19
    passo = max(passo_km, math.sqrt(larg * alt / massimo))
    gx, gy = max(4, round(larg / passo) + 1), max(4, round(alt / passo) + 1)
    lat = [A.N - r * (A.N - A.S) / (gy - 1) for r in range(gy)]
    lon = [A.O + c * (A.E - A.O) / (gx - 1) for c in range(gx)]
    return gy, gx, [(a, b) for a in lat for b in lon]


def prima_ora():
    """La prima ora del calcolo, in UTC: LENS_INIZIO se c'e', altrimenti adesso piu' LENS_DA."""
    testo = (os.environ.get("LENS_INIZIO") or "").strip().replace("Z", "")
    if testo:
        t = dt.datetime.fromisoformat(testo)
        return (t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)).astimezone(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    return dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0) + dt.timedelta(hours=int(os.environ.get("LENS_DA") or 0))


# quanti giorni chiedere al modello: fino all'ultima ora del calcolo (Open-Meteo conta i giorni da oggi)
GIORNI = int(min(10, max(3, math.ceil(((prima_ora() - dt.datetime.now(dt.timezone.utc)).total_seconds() / 3600
                                         + int(os.environ.get("LENS_ORE") or 15) + 24) / 24) + 1)))


def leggi(punti, modello, variabili, scelta, peso=1):
    """Una lettura di Open-Meteo per molti punti, a blocchi. Ritorna la lista delle risposte o None."""
    tutti = []
    blocco = max(10, 80 // peso)
    for i in range(0, len(punti), blocco):
        p = punti[i:i + blocco]
        url = ("https://api.open-meteo.com/v1/forecast?latitude=" + ",".join(f"{a:.4f}" for a, _ in p)
               + "&longitude=" + ",".join(f"{b:.4f}" for _, b in p) + "&hourly=" + ",".join(variabili)
               + f"&models={modello}&forecast_days={GIORNI}&timezone=UTC&wind_speed_unit=ms&cell_selection={scelta}")
        stato, d = scarica_json(url, timeout=90, tentativi=3)
        if stato != 200:
            print("lettura", modello, scelta, "rifiutata:", str(d)[:200])
            return None
        d = d if isinstance(d, list) else [d]
        if len(d) != len(p):
            return None
        tutti += d
    return tutti


def serie(dati, k, gy, gx):
    return np.array([[np.nan if x is None else x for x in d["hourly"].get(k) or [None] * len(d["hourly"]["time"])] for d in dati]).reshape(gy, gx, -1)


def leggi_youmeteo(percorso, gy, gx):
    """Il vento a 10 m di un file youmeteo (GRIB1 dal deposito privato: u e v ogni mezz'ora, maglia 0,055 gradi, niente
    raffica) sui punti del dominio. Ritorna le ore intere in UTC ("aaaa-mm-ggThh:00") e i campi (gy, gx, ore) in m/s."""
    import eccodes
    lat = np.array([A.N - r * (A.N - A.S) / (gy - 1) for r in range(gy)])
    lon = np.array([A.O + c * (A.E - A.O) / (gx - 1) for c in range(gx)])
    campi = {}
    with open(percorso, "rb") as f:
        while True:
            m = eccodes.codes_grib_new_from_file(f)
            if m is None:
                break
            try:
                par = eccodes.codes_get(m, "indicatorOfParameter")
                if par not in (33, 34) or eccodes.codes_get(m, "level") != 10:
                    continue
                vd, vt = eccodes.codes_get(m, "validityDate"), eccodes.codes_get(m, "validityTime")
                if vt % 100 != 0:
                    continue                                           # le mezze ore non servono
                t = f"{vd // 10000:04d}-{vd // 100 % 100:02d}-{vd % 100:02d}T{vt // 100:02d}:00"
                ni, nj = eccodes.codes_get(m, "Ni"), eccodes.codes_get(m, "Nj")
                la0, lo0 = eccodes.codes_get(m, "latitudeOfFirstGridPointInDegrees"), eccodes.codes_get(m, "longitudeOfFirstGridPointInDegrees")
                la1, lo1 = eccodes.codes_get(m, "latitudeOfLastGridPointInDegrees"), eccodes.codes_get(m, "longitudeOfLastGridPointInDegrees")
                val = eccodes.codes_get_values(m).reshape(nj, ni)
                val = np.where(np.abs(val) > 500, np.nan, val)
                fy = (lat - la0) / (la1 - la0) * (nj - 1)
                fx = (lon - lo0) / (lo1 - lo0) * (ni - 1)
                from scipy.ndimage import map_coordinates
                yy, xx = np.meshgrid(fy, fx, indexing="ij")
                campi.setdefault(t, {})["u" if par == 33 else "v"] = map_coordinates(val, [yy, xx], order=1, mode="nearest")
            finally:
                eccodes.codes_release(m)
    tempi = sorted(t for t, c in campi.items() if "u" in c and "v" in c)
    if not tempi:
        sys.exit("youmeteo: nessun campo di vento a 10 m nel file")
    u = np.stack([campi[t]["u"] for t in tempi], axis=-1)
    v = np.stack([campi[t]["v"] for t in tempi], axis=-1)
    return tempi, u, v


def riallinea(P, da_tempi, a_tempi):
    """Il profilo verticale sulle ore del vento in superficie: le ore che il profilo non ha restano vuote."""
    if P is None:
        return None
    pos = {t: k for k, t in enumerate(da_tempi)}
    idx = [pos.get(t, -1) for t in a_tempi]
    if all(k < 0 for k in idx):
        return None
    def prendi(a):
        out = np.full(a.shape[:-1] + (len(idx),), np.nan)
        for j, k in enumerate(idx):
            if k >= 0:
                out[..., j] = a[..., k]
        return out
    Q = dict(P)
    for v in ("V", "D", "T", "Z", "t2"):
        if Q.get(v) is not None:
            Q[v] = prendi(Q[v])
    return Q


def profilo_verticale(candidati):
    """Il profilo del primo modello di Open-Meteo che risponde: vento, direzione, temperatura e quota sui livelli di pressione."""
    var_p = [f"{v}_{p}hPa" for p in LIVELLI_P for v in ("wind_speed", "wind_direction", "temperature", "geopotential_height")]
    pgy, pgx, ppunti = griglia_punti(12.0, 64)
    for m in candidati + ["icon_eu", "gfs_global"]:
        profilo = leggi(ppunti, m, var_p + ["temperature_2m"], "nearest", peso=4)
        if profilo and not np.isnan(serie(profilo, "temperature_925hPa", pgy, pgx)[:, :, 6]).all():
            P = {"gy": pgy, "gx": pgx, "da": m, "t2": serie(profilo, "temperature_2m", pgy, pgx)}
            for v, k in (("V", "wind_speed"), ("D", "wind_direction"), ("T", "temperature"), ("Z", "geopotential_height")):
                P[v] = np.stack([serie(profilo, f"{k}_{p}hPa", pgy, pgx) for p in LIVELLI_P])
            print("profilo verticale da:", m, "· livelli con dati:", [LIVELLI_P[k] for k in range(len(LIVELLI_P)) if not np.isnan(P["V"][k]).all()])
            return P, profilo[0]["hourly"]["time"]
    print("profilo verticale: nessun modello ha risposto")
    return None, []


def modello_youmeteo(percorso):
    """youmeteo (Giano, 20/11): vento a 10 m dal file del deposito, profilo verticale e stabilita' da ICON-2I."""
    gy, gx, _ = griglia_punti(5.5, 500)
    tempi, u, v = leggi_youmeteo(percorso, gy, gx)
    vel = np.hypot(u, v)
    dire = np.arctan2(-u, -v) % (2 * np.pi)                          # da dove viene, come Open-Meteo
    P, tempi_p = profilo_verticale(["italia_meteo_arpae_icon_2i"])
    P = riallinea(P, tempi_p, tempi)
    vuoto = np.full(vel.shape, np.nan)
    print(f"youmeteo: {len(tempi)} ore, da {tempi[0]} a {tempi[-1]}")
    return "youmeteo", tempi, {"gy": gy, "gx": gx, "v": vel, "d": dire, "g": vuoto, "vt": vel, "dt": dire, "gt": vuoto}, P


def modello():
    """Superficie (vento e raffica a 10 m, due letture: mare e terra) e profilo verticale (8 livelli di pressione)."""
    scelto = os.environ.get("LENS_MODELLO") or "italia_meteo_arpae_icon_2i"
    if scelto == "youmeteo":
        percorso = os.environ.get("LENS_FILE") or ""
        if not os.path.exists(percorso):
            sys.exit("youmeteo: il file del deposito non e' stato scaricato")
        return modello_youmeteo(percorso)
    candidati = [scelto] + [m for m in ("italia_meteo_arpae_icon_2i", "icon_eu", "ecmwf_ifs") if m != scelto]
    var_p = [f"{v}_{p}hPa" for p in LIVELLI_P for v in ("wind_speed", "wind_direction", "temperature", "geopotential_height")]
    pgy, pgx, ppunti = griglia_punti(12.0, 64)
    profilo, da = None, None
    for m in candidati + ["icon_eu", "gfs_global"]:
        profilo = leggi(ppunti, m, var_p + ["temperature_2m"], "nearest", peso=4)
        if profilo and not np.isnan(serie(profilo, "temperature_925hPa", pgy, pgx)[:, :, 6]).all():
            da = m
            break
    print("profilo verticale da:", da)
    time.sleep(62)   # Open-Meteo conta ogni punto come una richiesta, con un limite di 600 al minuto
    sup = None
    for m in candidati:
        gy, gx, punti = griglia_punti(RISOLUZIONE_KM.get(m, 7.0), 500)
        var = ["wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"]
        extra = ["precipitation", "cape"]
        mare = leggi(punti, m, var + extra, "sea") or leggi(punti, m, var + extra, "nearest")
        if mare and not np.isnan(serie(mare, "wind_speed_10m", gy, gx)[:, :, 6]).all():
            time.sleep(62)
            terra = leggi(punti, m, var, "land") or mare
            sup = (m, gy, gx, mare, terra)
            break
        time.sleep(62)
    if not sup:
        sys.exit("Nessun modello letto")
    m, gy, gx, mare, terra = sup
    tempi = mare[0]["hourly"]["time"]
    S = lambda d, k: serie(d, k, gy, gx)
    P = {"gy": pgy, "gx": pgx, "da": da, "t2": serie(profilo, "temperature_2m", pgy, pgx) if profilo else None}
    if profilo:
        for v, k in (("V", "wind_speed"), ("D", "wind_direction"), ("T", "temperature"), ("Z", "geopotential_height")):
            P[v] = np.stack([serie(profilo, f"{k}_{p}hPa", pgy, pgx) for p in LIVELLI_P])   # (livelli, gy, gx, ore)
        pieni = [k for k, p in enumerate(LIVELLI_P) if not all(np.isnan(P[v][k]).all() for v in ("V", "Z"))]
        print("livelli di pressione con dati:", [LIVELLI_P[k] for k in pieni])
        P = riallinea(P, profilo[0]["hourly"]["time"], tempi)
    return m, tempi, {"gy": gy, "gx": gx, "v": S(mare, "wind_speed_10m"), "d": np.radians(S(mare, "wind_direction_10m")),
                      "g": S(mare, "wind_gusts_10m"), "vt": S(terra, "wind_speed_10m"), "dt": np.radians(S(terra, "wind_direction_10m")),
                      "gt": S(terra, "wind_gusts_10m"), "pr": S(mare, "precipitation"), "cape": S(mare, "cape")}, P


def fine(campo):
    """Interpolazione bilineare da una griglia di punti del modello alla griglia fine."""
    from scipy.ndimage import map_coordinates
    gy, gx = campo.shape
    jj, ii = np.indices((A.NY, A.NX), dtype=float)
    c = np.where(np.isnan(campo), np.nanmean(campo), campo)
    return map_coordinates(c, [(jj + 0.5) / A.NY * (gy - 1), (ii + 0.5) / A.NX * (gx - 1)], order=1, mode="nearest")


def liscia(campo, km=4.0):
    """Filtro gaussiano di circa [km] chilometri su un campo ai punti del modello (i buchi prendono la media)."""
    from scipy.ndimage import gaussian_filter
    gy, gx = campo.shape
    passo = max((A.E - A.O) * A.kml / max(gx - 1, 1), (A.N - A.S) * 111.19 / max(gy - 1, 1))
    c = np.where(np.isnan(campo), np.nanmean(campo), campo)
    return gaussian_filter(c, km / passo, mode="nearest")


def componenti(vel, dire):
    return -vel * np.sin(dire), -vel * np.cos(dire)


# ---------------------------------------------------------------- stabilita'
GRADINI = np.array([0.03, 0.06, 0.12, 0.18, 0.25, 0.35, 0.5, 0.7, 1.0])


def profilo_alfa2(zc, h_ril, fr_b, fr_a):
    """alfa2 livello per livello: quasi orizzontale sotto la linea divisoria, Fr^2 fino alla cima, Fr^2 dello strato
    alto sopra. La quota della linea si arrotonda a 50 m, cosi' tra un'ora e l'altra la matrice si riusa."""
    hd = max(BLOCCO_MIN, 1.0 - fr_b) * h_ril if np.isfinite(fr_b) else BLOCCO_MIN * h_ril
    hd = round(min(hd, 0.95 * h_ril) / 50.0) * 50.0
    a_mid = float(np.clip(gradino(fr_b ** 2), 0.06, 0.5))
    a_alto = float(np.clip(gradino(fr_a ** 2), 0.25, 1.0))
    return np.where(zc <= hd, ALFA2_BLOCCATO, np.where(zc <= h_ril, a_mid, a_alto)), hd, a_mid, a_alto


def gradino(a2):
    return float(GRADINI[np.argmin(np.abs(np.log(GRADINI) - math.log(float(np.clip(a2, 0.03, 1.0)))))])


def validi(P, i):
    """Livelli di pressione con dati in quest'ora (vento, direzione, temperatura e quota)."""
    return [k for k in range(len(LIVELLI_P))
            if all(np.isfinite(P[v][k, :, :, i]).any() for v in ("V", "D", "T", "Z"))]


# Stabilita' "efficace" minima e massima (1/s). La minima vale anche con aria rimescolata: su rilievi ripidi l'aria
# vicino al suolo non scavalca comunque (si stacca e gira attorno), e un modello a conservazione di massa non lo vede.
# 0,010 sta tra i valori efficaci tarati in Shift sui racconti di Giano alle Eolie (0,008 instabile, 0,015 normale).
N_MIN, N_MAX = 0.010, 0.030
# Strato bloccato (21/11, dopo la prova delle Eolie: "il vento deve piegarsi attorno alle isole e incanalarsi").
# Sotto la linea di corrente divisoria Hd = H (1 - Fr) l'aria non ha l'energia per salire e gira attorno al rilievo
# (Sheppard 1956; e' lo schema di CALMET). Hd non scende mai sotto meta' del rilievo: sui fianchi ripidi delle isole
# il flusso si stacca e gira attorno anche con vento teso, cosa che la sola conservazione della massa non vede.
# Questo minimo e' un'ipotesi, da tarare: con meta' isola bloccata, su un'isola di prova di 600 m con 15 nodi
# vengono +25-35% ai capi e +45% in un canale di un chilometro, i valori che si raccontano a vela.
BLOCCO_MIN = 0.5
ALFA2_BLOCCATO = 0.005


def stabilita(P, i, h_rilievi):
    """Froude e alfa2 in due strati: dal suolo alla cima dei rilievi (H) e da H a 2,5 H.
    N dalla differenza di temperatura potenziale tra i livelli del modello che racchiudono lo strato (media sul
    dominio). La temperatura a 2 m NON entra: sul mare d'autunno e' piu' calda dell'aria e faceva sembrare instabile
    tutto lo strato (versione del 20/11: Fr 9,9 fisso, e il vento scavalcava le isole quasi senza piegarsi).
    Fr = U / (N H); alfa2 = Fr^2 tra 0,03 e 1 (1 = flusso potenziale: l'aria non scavalca mai piu' facilmente di cosi'),
    a gradini, cosi' la parte costosa si riusa tra le ore. Ritorna, per strato, (Fr, alfa2, N del modello)."""
    ks = validi(P, i) if P is not None else []
    if len(ks) < 2:
        fr = 5.0 / (N_MIN * h_rilievi)
        return (fr, gradino(fr ** 2), float("nan")), (fr, gradino(fr ** 2), float("nan"))
    Z = np.array([np.nanmean(P["Z"][k, :, :, i]) for k in ks])
    T = np.array([np.nanmean(P["T"][k, :, :, i]) for k in ks]) + 273.15
    th = T * (1000.0 / np.array([LIVELLI_P[k] for k in ks])) ** 0.286
    U = np.array([np.nanmean(P["V"][k, :, :, i]) for k in ks])

    def strato(z0_, z1_):
        ia = max(0, int(np.searchsorted(Z, z0_, side="right")) - 1)          # il livello sotto la base (o il piu' basso)
        ib = min(len(Z) - 1, int(np.searchsorted(Z, z1_, side="left")))     # il primo livello sopra la cima
        if ib <= ia:
            ib = min(len(Z) - 1, ia + 1)
            ia = max(0, ib - 1)
        dth = (th[ib] - th[ia]) / max(Z[ib] - Z[ia], 50.0)
        n_mod = math.sqrt(max(9.81 / float(th[ia:ib + 1].mean()) * dth, 0.0))
        n = min(max(n_mod, N_MIN), N_MAX)
        u = float(np.mean(U[ia:ib + 1]))
        fr = max(u, 0.5) / (n * h_rilievi)
        return fr, gradino(fr ** 2), n_mod

    return strato(0.0, h_rilievi), strato(h_rilievi, 2.5 * h_rilievi)


# ---------------------------------------------------------------- campo di partenza 3D
def iniziale(h, z0, zc, u10, v10, P, i):
    """Strato superficiale: profilo logaritmico dal vento a 10 m fino a 100 m dal suolo. Sopra: il profilo del modello
    ai livelli di pressione, interpolato in quota assoluta e punto per punto; raccordo tra 100 e 400 m dal suolo."""
    agl = zc[:, None, None] - h[None]
    flog = np.log(np.clip(agl, 10.0, 100.0) / z0[None]) / np.log(10.0 / z0)[None]
    u = (u10[None] * flog).astype(np.float32)
    v = (v10[None] * flog).astype(np.float32)
    ks = validi(P, i) if P is not None else []
    if len(ks) < 2:
        return u, v
    Zf = np.stack([fine(P["Z"][k, :, :, i]) for k in ks])
    up, vp = componenti(P["V"][:, :, :, i], np.radians(P["D"][:, :, :, i]))
    Uf = np.stack([fine(up[k]) for k in ks])
    Vf = np.stack([fine(vp[k]) for k in ks])
    for k, z in enumerate(zc):
        peso = np.clip((agl[k] - 100.0) / 300.0, 0.0, 1.0)
        if not peso.any():
            continue
        ua, va = Uf[0].copy(), Vf[0].copy()
        for j in range(len(ks) - 1):
            dentro = (z > Zf[j]) & (z <= Zf[j + 1])
            w = np.where(dentro, (z - Zf[j]) / np.maximum(Zf[j + 1] - Zf[j], 1.0), 0.0)
            ua = np.where(dentro, Uf[j] + (Uf[j + 1] - Uf[j]) * w, ua)
            va = np.where(dentro, Vf[j] + (Vf[j + 1] - Vf[j]) * w, va)
        sopra = z > Zf[-1]
        ua, va = np.where(sopra, Uf[-1], ua), np.where(sopra, Vf[-1], va)
        u[k] = u[k] * (1 - peso) + ua * peso
        v[k] = v[k] * (1 - peso) + va * peso
    return u, v


# ---------------------------------------------------------------- uscite
def b64(a):
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def grib(nome, tempi_ore, campi, t0):
    """GRIB2 su griglia regolare lat/lon (il riquadro senza margine): u, v e raffica a 10 m, un messaggio per ora."""
    import eccodes
    s, n, o, e = A.interno
    ny, nx = campi[0][0].shape
    with open(nome, "wb") as f:
        for passo, (u, v, g) in zip(tempi_ore, campi):
            for numero, val in ((2, u), (3, v), (22, g)):
                m = eccodes.codes_grib_new_from_samples("regular_ll_sfc_grib2")
                for k, x in (("centre", 255), ("subCentre", 0), ("generatingProcessIdentifier", 1), ("discipline", 0), ("parameterCategory", 2), ("parameterNumber", numero),
                             ("typeOfFirstFixedSurface", 103), ("scaleFactorOfFirstFixedSurface", 0), ("scaledValueOfFirstFixedSurface", 10),
                             ("dataDate", int(t0.strftime("%Y%m%d"))), ("dataTime", int(t0.strftime("%H%M"))),
                             ("stepUnits", 1), ("forecastTime", int(passo)), ("Ni", nx), ("Nj", ny),
                             ("latitudeOfFirstGridPointInDegrees", n - (n - s) / ny / 2), ("longitudeOfFirstGridPointInDegrees", o + (e - o) / nx / 2),
                             ("latitudeOfLastGridPointInDegrees", s + (n - s) / ny / 2), ("longitudeOfLastGridPointInDegrees", e - (e - o) / nx / 2),
                             ("iDirectionIncrementInDegrees", (e - o) / nx), ("jDirectionIncrementInDegrees", (n - s) / ny),
                             ("jScansPositively", 0), ("packingType", "grid_simple"), ("bitsPerValue", 12)):
                    eccodes.codes_set(m, k, x)
                eccodes.codes_set_values(m, np.asarray(val, dtype=float).ravel())
                eccodes.codes_write(m, f)
                eccodes.codes_release(m)


def main():
    from scipy.ndimage import gaussian_filter
    t_inizio = time.time()
    print(f"area: {A.nome} · dominio {A.S:.3f}-{A.N:.3f} N, {A.O:.3f}-{A.E:.3f} E · {A.NY} x {A.NX} celle da {A.dx:.0f} m")
    h, z0, mare, carta, nomi = terreno()
    terra = ~mare
    # la quota che fa da sbarramento: quasi la cima piu' alta (per un'isola conta la cima, non la media dei pendii)
    h_ril = float(max(200.0, min(1800.0, max(np.percentile(h[terra], 98), 0.85 * h.max()) if terra.any() else 200.0)))
    print(f"terreno: quota massima {h.max():.0f} m, sbarramento {h_ril:.0f} m, mare {mare.mean() * 100:.0f}%")
    usato, tempi, M, P = modello()
    dz, zc = livelli()
    ora = prima_ora()
    chiave = ora.strftime("%Y-%m-%dT%H:%M")
    if chiave not in tempi:
        sys.exit(f"Il modello {usato} non ha l'ora chiesta ({chiave} UTC): va da {tempi[0]} a {tempi[-1]}")
    i0 = tempi.index(chiave)
    m = A.m
    dentro = (slice(m, A.NY - m), slice(m, A.NX - m))
    ny, nx = A.NY - 2 * m, A.NX - 2 * m
    s_, n_, o_, e_ = A.interno
    fx = lambda lo: (lo - o_) / (e_ - o_)
    fy = lambda la: (n_ - la) / (n_ - s_)
    # le celle di mare lontane piu' di 5 km dalla costa, per tarare le raffiche sul modello
    from scipy.ndimage import distance_transform_edt
    largo = distance_transform_edt(mare) * A.dx > 5000
    dist_mare = distance_transform_edt(mare) * A.dx      # metri dalla costa, sul mare (0 a terra)
    # Lens 2: libreria del radar per l'area e il modello (se c'e')
    lib2 = None
    try:
        from lens.radar import Libreria, campo as campo_radar
        f2 = os.environ.get("LENS2_LIB") or ""
        if f2 and os.path.exists(f2):
            lib2 = Libreria(f2)
            print(f"Lens 2: libreria {lib2.area} · {lib2.modello} · {lib2.nc} celle, {lib2.ns} passaggi")
    except Exception as e:
        print("Lens 2 non usato:", e)
    lat_f, lon_f = A.lat_lon_fine()
    lat_m = np.linspace(A.N, A.S, M["gy"]); lon_m = np.linspace(A.O, A.E, M["gx"])
    ore, memoria, campi_grib, passi = [], {}, [], []
    for passo in range(int(os.environ.get("LENS_ORE") or 15)):
        i = i0 + passo
        if i >= len(tempi) or np.isnan(M["v"][:, :, i]).all():
            break
        # Il modello ha gia' una sua idea grossolana delle isole e delle coste (ridossi larghi chilometri, spostati):
        # si liscia il suo vento a 10 m su circa 4 km, cosi' resta il flusso d'insieme e il dettaglio lo mette Lens,
        # una volta sola e nel punto giusto.
        um, vm = componenti(M["v"][:, :, i], M["d"][:, :, i])
        ut, vt = componenti(M["vt"][:, :, i], M["dt"][:, :, i])
        um, vm, ut, vt = liscia(um), liscia(vm), liscia(ut), liscia(vt)
        u10 = np.where(mare, fine(um), fine(ut))
        v10 = np.where(mare, fine(vm), fine(vt))
        s10 = np.where(mare, fine(liscia(M["v"][:, :, i])), fine(liscia(M["vt"][:, :, i])))
        k = s10 / np.maximum(np.hypot(u10, v10), 0.05)   # l'interpolazione dei vettori non deve togliere velocita'
        u10, v10 = u10 * k, v10 * k
        (fr_b, a2_b, n_b), (fr_a, a2_a, n_a) = stabilita(P, i, h_ril)
        alfa2, hd, a2_b, a2_a = profilo_alfa2(zc, h_ril, fr_b, fr_a)
        u3, v3 = iniziale(h, z0, zc, u10, v10, P, i)
        t1 = time.time()
        u, v, w, aria, (d0, d1) = aggiusta(h, u3, v3, A.dx, dz, zc, alfa2=alfa2, memoria=memoria)
        del u3, v3
        us, vs = al_suolo(u, v, aria, h, zc, z0)
        del u, v, w, aria
        us, vs = gaussian_filter(us, 1.0), gaussian_filter(vs, 1.0)   # toglie il rumore da gradino della griglia a scalini
        giro = None
        if RILIEVO != 1.0:
            # Sul mare il peso del rilievo e' quello di Lens 0.54 (tarato sul radar, e la correzione del radar va sopra
            # questo); a terra, dove il radar non misura, resta il rilievo pieno, che si vede nel flusso.
            wr = np.where(mare, RILIEVO, 1.0)
            uf, vf = us, vs                                            # il rilievo pieno
            us, vs = u10 + (us - u10) * wr, v10 + (vs - v10) * wr
            if DIR_RIL > 0:                                            # 0.56: la sua direzione, applicata alla fine
                giro = DIR_RIL * ((np.arctan2(uf, vf) - np.arctan2(us, vs) + np.pi) % (2 * np.pi) - np.pi)
            del uf, vf
        fatt, sx = scia(h, us, vs, A.dx, fr_b, profondita=RIDOSSO, s_max=RIDOSSO_S)
        c_ibl = 0.9 if fr_b >= 1.0 else (0.6 if fr_b >= 0.5 else 0.35)
        fcosta, _, rec, z0l = costa(mare, z0, us, vs, A.dx, c=c_ibl)
        fcosta = 1.0 - COSTA * (1.0 - fcosta)
        f = np.minimum(fatt, fcosta)
        us, vs = us * f, vs * f
        # Sugli spigoli vivi (un capo in una sola cella) la conservazione della massa esagera: non piu' del 60% sopra il
        # vento del modello. Sulle Eolie del 20/11 riguardava 22 celle su 74.000.
        tetto = np.minimum(1.0, 1.6 * np.maximum(s10, 0.5) / np.maximum(np.hypot(us, vs), 1e-6))
        us, vs = us * tetto, vs * tetto
        info2 = None
        if lib2 is not None:
            from scipy.interpolate import RegularGridInterpolator
            u0m, v0m = componenti(M["v"][:, :, i], M["d"][:, :, i])
            pts = np.stack([lib2.lat, lib2.lon], axis=1)
            uc = RegularGridInterpolator((lat_m[::-1], lon_m), np.nan_to_num(u0m)[::-1], bounds_error=False, fill_value=None)(pts)
            vc = RegularGridInterpolator((lat_m[::-1], lon_m), np.nan_to_num(v0m)[::-1], bounds_error=False, fill_value=None)(pts)
            if P is not None and np.isfinite(P["V"][3][:, :, i]).any():
                u9, v9 = componenti(P["V"][3][:, :, i], np.radians(P["D"][3][:, :, i]))
                u925, v925 = float(np.nanmean(u9)), float(np.nanmean(v9))
            else:
                u925, v925 = float(np.mean(uc)), float(np.mean(vc))
            # 0.58 (Giano, 26/11): con il rilievo sotto, il radar fissa solo il livello a grande scala (30 km), il disegno resta di Lens
            rel = (np.hypot(us, vs), mare, s10) if RILIEVO > 0 else None
            g2, info2 = campo_radar(lib2, uc, vc, u925, v925, int(tempi[i][11:13]), lat_f, lon_f, lens=rel)
            g2 = np.where(mare, g2, 1.0)
            us, vs = us * g2, vs * g2
        if giro is not None:                                           # la direzione del rilievo pieno, forza invariata
            cg, sg = np.cos(giro), np.sin(giro)
            us, vs = us * cg + vs * sg, -us * sg + vs * cg
        vel = np.hypot(us, vs)
        # raffiche: fattore di picco dal modello stesso, sul mare aperto
        gm = np.where(mare, fine(M["g"][:, :, i]), fine(M["gt"][:, :, i]))
        ok = largo & (s10 > 3.0) & np.isfinite(gm)
        rapp = float(np.median(gm[ok] / s10[ok])) if ok.sum() > 50 else 1.3
        ti_mare = float(np.clip((rapp - 1.0) / 3.0, 0.05, 0.3))
        raff, ti = raffiche(vel, mare, z0, rec, z0l, fatt, ti_mare)
        kn, gkn = vel[dentro] * 1.944, raff[dentro] * 1.944
        dd = (np.degrees(np.arctan2(-us, -vs)) % 360)[dentro]
        q = None
        if P is not None and np.isfinite(P["V"][3][P["gy"] // 2, P["gx"] // 2, i]):
            c_ = (P["gy"] // 2, P["gx"] // 2)
            q = [round(float(P["V"][3][c_][i]) * 1.944), round(float(P["D"][3][c_][i]))]
        ore.append({"t": tempi[i], "fr": round(fr_b, 2), "a2": a2_b, "fr2": round(fr_a, 2), "a22": a2_a} if not PAGINA else
                   {"t": tempi[i], "fr": round(fr_b, 2), "a2": a2_b, "fr2": round(fr_a, 2), "a22": a2_a,
                    "v": b64(np.clip(np.round(kn * 4), 0, 255).astype(np.uint8)),
                    "g": b64(np.clip(np.round(gkn * 4), 0, 255).astype(np.uint8)),
                    "d": b64(np.round(dd / 360 * 256).astype(np.int64).astype(np.uint8)),
                    "r": b64(np.packbits((sx[dentro] > 18).ravel())),
                    "mv": [round(float(x) * 1.944, 1) for x in np.nan_to_num(M["v"][:, :, i]).ravel()],
                    "md": [round(float(x)) for x in np.degrees(np.nan_to_num(M["d"][:, :, i])).ravel()], "q": q,
                    "pr": [round(float(x), 1) for x in np.nan_to_num(M["pr"][:, :, i]).ravel()] if "pr" in M else None,
                    "ca": [round(float(x)) for x in np.nan_to_num(M["cape"][:, :, i]).ravel()] if "cape" in M else None,
                    "l2": info2})
        campi_grib.append((us[dentro], vs[dentro], raff[dentro]))
        passi.append(passo)                # ore dalla prima ora del calcolo, che e' la data del GRIB
        sm = mare[dentro]
        print(tempi[i], f"basso N {n_b:.4f} Fr {fr_b:.2f} bloccato fino a {hd:.0f} m, poi alfa2 {a2_b} · alto N {n_a:.4f} Fr {fr_a:.2f} alfa2 {a2_a} · div {d0:.1e}->{d1:.1e} · {time.time() - t1:.0f} s"
              f" · mare: modello {s10[dentro][sm].mean() * 1.944:.1f} kn, Lens {kn[sm].min():.1f}/{kn[sm].mean():.1f}/{kn[sm].max():.1f} kn"
              f" · raffica/vento del modello al largo {rapp:.2f} (turbolenza {ti_mare:.3f}), Lens al largo {float(np.median((raff / np.maximum(vel, 0.1))[largo])):.2f}, sotto costa max {float((raff / np.maximum(vel, 0.1))[mare & ~largo].max()):.2f}")
    viste = {}
    for nome, r in A.viste.items():
        if r is None:
            viste[nome] = [0, 0, nx, ny]
        else:
            x0, x1 = max(0, int(fx(r[2]) * nx)), min(nx, int(fx(r[3]) * nx))
            y0, y1 = max(0, int(fy(r[1]) * ny)), min(ny, int(fy(r[0]) * ny))
            viste[nome] = [x0, y0, x1 - x0, y1 - y0]
    pacco = {"ore": ore, "quota": b64(np.clip(h[dentro], 0, 65535).astype("<u2")), "mare": b64(np.packbits(mare[dentro].ravel()))} if PAGINA else {}
    dati = {"nx": nx, "ny": ny, "dx": A.dx, "m": m, "NX": A.NX, "NY": A.NY, "gx": M["gx"], "gy": M["gy"], "kb": A.kb, "modello": usato,
            "nome_modello": NOMI_MODELLI.get(usato, usato), "quota_da": P["da"] if P else None, "titolo": A.nome,
            "generato": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"), "n_ore": len(ore), "viste": viste,
            "luoghi": nomi, "casa": PALERMO.get("casa"), "interno": A.interno, "lens2": lib2 is not None, "gz": base64.b64encode(gzip.compress(json.dumps(pacco, separators=(",", ":")).encode(), 9)).decode()}
    uscita = os.path.join(QUI, "uscita")
    os.makedirs(uscita, exist_ok=True)
    if not campi_grib:
        sys.exit(f"Il modello {usato} non ha dati per le ore chieste (da {chiave} UTC)")
    if os.environ.get("LENS_SALVA"):
        # per l'insieme di piu' modelli: si salva tutto e la pagina la fa lens/unisci.py
        json.dump({"dati": dati, "carta": carta}, open(os.environ["LENS_SALVA"], "w"), separators=(",", ":"))
        print("salvato per l'insieme:", os.environ["LENS_SALVA"])
        return
    if PAGINA:
        from lens.pagina import pagina
        open(os.path.join(uscita, "pagina.html"), "w", encoding="utf-8").write(pagina(dati, carta, "image/webp"))
    nome_grib = os.path.join(uscita, f"lens_{ID}.grb2" if ID else "lens.grb2")
    try:
        grib(nome_grib, passi, campi_grib, dt.datetime.fromisoformat(tempi[i0]))
        print("GRIB scritto:", os.path.getsize(nome_grib) // 1024, "KB,", len(campi_grib), "ore")
    except Exception as e:
        print("GRIB non scritto:", e)
    json.dump({k: v for k, v in dati.items() if k not in ("gz", "luoghi", "viste")}
              | {"area": [round(x, 5) for x in A.interno], "inizio": tempi[i0], "id": ID,
                 "ore": [{x: o[x] for x in ("t", "fr", "a2", "fr2", "a22")} for o in ore], "minuti": round((time.time() - t_inizio) / 60, 1)},
              open(os.path.join(uscita, f"lens_{ID}.json" if ID else "riassunto.json"), "w"), indent=1)

if __name__ == "__main__":
    main()

"""Carta di base (una tantum): rilievo vero, boschi, abitati, acqua, fiumi, paesi, cime.
Fonti: Copernicus DEM GLO-30 (ESA/Copernicus), ESA WorldCover 2021 v200 (CC BY 4.0),
OpenStreetMap (ODbL) via Overpass. Scrive mappa/base/base.jpg e mappa/base/base.json."""
import base64, json, math, os, sys, urllib.parse, urllib.request
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from comune.base import casa, UA, SUF
from mappa.geo import riquadro, LATI

QUI = os.path.dirname(__file__)
NB = 1500   # pixel di lavoro
NOUT = 1000  # pixel dell'immagine salvata
NDEM = 150  # lato del rilievo passato alla pagina
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
os.environ.setdefault("AWS_NO_SIGN_REQUEST", "YES")


def mosaico(urls_di_tessera, passo, bbox, ricampiona, tipo, vuoto):
    import rasterio
    from rasterio.windows import from_bounds
    s, n, o, e = bbox
    fuori = np.full((NB, NB), vuoto, dtype=tipo)
    lat0 = math.floor(s / passo) * passo
    while lat0 < n:
        lon0 = math.floor(o / passo) * passo
        while lon0 < e:
            w1, e1, s1, n1 = max(o, lon0), min(e, lon0 + passo), max(s, lat0), min(n, lat0 + passo)
            c0, c1 = round((w1 - o) / (e - o) * NB), round((e1 - o) / (e - o) * NB)
            r0, r1 = round((n - n1) / (n - s) * NB), round((n - s1) / (n - s) * NB)
            if c1 > c0 and r1 > r0:
                url = urls_di_tessera(lat0, lon0)
                with rasterio.open(url) as ds:
                    a = ds.read(1, window=from_bounds(w1, s1, e1, n1, ds.transform), out_shape=(r1 - r0, c1 - c0),
                                resampling=ricampiona, boundless=True)
                fuori[r0:r1, c0:c1] = a
                print("letta", os.path.basename(url), a.shape)
            lon0 += passo
        lat0 += passo
    return fuori


def ns(v):
    return ("N" if v >= 0 else "S") + f"{abs(int(v)):02d}"


def eo(v):
    return ("E" if v >= 0 else "W") + f"{abs(int(v)):03d}"


def rilievo(bbox):
    from rasterio.enums import Resampling
    def url(la, lo):
        nome = f"Copernicus_DSM_COG_10_{ns(la)}_00_{eo(lo)}_00_DEM"
        return f"https://copernicus-dem-30m.s3.amazonaws.com/{nome}/{nome}.tif"
    return mosaico(url, 1, bbox, Resampling.bilinear, np.float32, 0).astype(np.float32)


def copertura(bbox):
    from rasterio.enums import Resampling
    def url(la, lo):
        return f"https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{ns(la)}{eo(lo)}_Map.tif"
    return mosaico(url, 3, bbox, Resampling.mode, np.uint8, 0)


def osm(bbox, lato):
    s, n, o, e = bbox
    # riquadro arrotondato verso l'esterno: a Overpass non arriva il centro esatto
    b = f"{math.floor(s * 10) / 10},{math.floor(o * 10) / 10},{math.ceil(n * 10) / 10},{math.ceil(e * 10) / 10}"
    acque = "river" if lato > 30 else "^(river|stream)$"
    op = "=" if lato > 30 else "~"
    q = (f'[out:json][timeout:90];(way["waterway"{op}"{acque}"]({b});node["place"~"^(town|village)$"]({b});'
         f'node["natural"="peak"]["name"]["ele"]({b}););out geom;')
    for server in ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
                   "https://maps.mail.ru/osm/tools/overpass/api/interpreter", "https://overpass.private.coffee/api/interpreter"):
        for metodo in ("POST", "GET"):
            try:
                if metodo == "POST":
                    req = urllib.request.Request(server, data=urllib.parse.urlencode({"data": q}).encode(), headers=UA)
                else:
                    req = urllib.request.Request(server + "?" + urllib.parse.urlencode({"data": q}), headers=UA)
                with urllib.request.urlopen(req, timeout=120) as r:
                    return json.loads(r.read())["elements"]
            except Exception as ex:
                ERRORI.append(f"{server.split('/')[2]} {metodo}: {type(ex).__name__}: {str(ex)[:120]}")
                print("Overpass", ERRORI[-1])
    return []


ERRORI = []


# Tinte per quota prese da Shift (carta scolastica: verde chiaro in basso, giallo e ocra in collina, bruno in alto),
# con le fasce strette sulle quote di questa zona, che va da 200 a 1100 m.
RAMPA = [(200, (0xD3, 0xE0, 0xB8)), (300, (0xDE, 0xE5, 0xBE)), (420, (0xEA, 0xE3, 0xB6)), (560, (0xE3, 0xCF, 0xA2)),
         (720, (0xD3, 0xB9, 0x8C)), (900, (0xBF, 0x9F, 0x7C)), (1100, (0xAB, 0x8D, 0x73)), (1400, (0xC2, 0xB8, 0xAE))]


def tinte(z):
    q = np.array([p[0] for p in RAMPA], dtype=np.float32)
    return np.stack([np.interp(z, q, [p[1][k] for p in RAMPA]) for k in range(3)], axis=-1)


def carta(lat, lon, quota, lato):
    bbox = riquadro(lat, lon, lato)
    s, n, o, e = bbox
    z = rilievo(bbox)
    try:
        cov = copertura(bbox)
    except Exception as ex:
        print("WorldCover non letto:", type(ex).__name__, ex)
        cov = np.zeros((NB, NB), np.uint8)
    rgb = tinte(z)
    def mescola(maschera, colore, k):
        rgb[maschera] = rgb[maschera] * (1 - k) + np.array(colore, np.float32) * k
    mescola(cov == 10, (126, 164, 110), 0.50)  # bosco: velo verde, la tinta di quota resta leggibile sotto
    mescola(cov == 50, (206, 150, 140), 0.60)  # abitato: grigio rosato
    mescola(cov == 80, (120, 172, 222), 0.92)  # acqua
    # ombreggiatura come in Shift: luce da nord-ovest alta 45 gradi, mai troppo scura
    passo = lato * 1000 / NB
    esag = 3.2 if lato > 30 else 2.6
    gy, gx = np.gradient(z, passo)
    dzdx, dzdy = gx * esag, -gy * esag
    rel = np.clip((0.5 * dzdx - 0.5 * dzdy + 0.7071) / np.sqrt(dzdx ** 2 + dzdy ** 2 + 1.0) / 0.7071, 0.0, 1.45)
    rgb *= np.clip(0.52 + 0.48 * rel, 0.55, 1.16)[..., None]
    # curve di livello brune, piu' marcate le direttrici
    inchiostro = np.array((0x7A, 0x5A, 0x3C), np.float32)
    passo_curve, direttrici = (100, 500) if lato > 30 else (50, 250)
    def curve(intervallo, forza):
        liv = np.floor(z / intervallo)
        bordo = np.zeros(liv.shape, dtype=bool)
        bordo[:-1, :] |= liv[:-1, :] != liv[1:, :]
        bordo[:, :-1] |= liv[:, :-1] != liv[:, 1:]
        rgb[bordo] = rgb[bordo] * (1 - forza) + inchiostro * forza
    curve(passo_curve, 0.34)
    curve(direttrici, 0.62)
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    px = lambda la, lo: ((lo - o) / (e - o) * NB, (n - la) / (n - s) * NB)
    el = osm(bbox, lato)
    d = ImageDraw.Draw(img)
    fiumi = 0
    for x in el:
        if x.get("type") == "way" and x.get("geometry"):
            grosso = x.get("tags", {}).get("waterway") == "river"
            if not grosso and not x.get("tags", {}).get("name"):
                continue  # i rigagnoli senza nome riempirebbero la carta
            d.line([px(g["lat"], g["lon"]) for g in x["geometry"]], fill=(66, 128, 204), width=4 if grosso else 3, joint="curve")
            fiumi += 1
    dentro = lambda la, lo: s < la < n and o < lo < e
    paesi, cime = [], []
    for x in el:
        if x.get("type") != "node" or not dentro(x["lat"], x["lon"]):
            continue
        t = x.get("tags", {})
        fx, fy = (x["lon"] - o) / (e - o), (n - x["lat"]) / (n - s)
        if t.get("place") in ("town", "village") and t.get("name"):
            pop = 0
            try:
                pop = int(str(t.get("population", "0")).replace(" ", ""))
            except ValueError:
                pass
            paesi.append({"n": t["name"], "x": round(fx, 4), "y": round(fy, 4), "c": 1 if t["place"] == "town" else 0, "p": pop})
        elif t.get("natural") == "peak":
            try:
                cime.append({"n": t["name"], "x": round(fx, 4), "y": round(fy, 4), "q": round(float(str(t["ele"]).replace(",", ".").split()[0]))})
            except ValueError:
                pass
    def sfoltisci(v, chiave, dmin, massimo):
        scelti = []
        for p in sorted(v, key=chiave, reverse=True):
            if all(math.hypot(p["x"] - q["x"], p["y"] - q["y"]) > dmin for q in scelti) and 0.04 < p["x"] < 0.96 and 0.04 < p["y"] < 0.96:
                scelti.append(p)
            if len(scelti) >= massimo:
                break
        return scelti
    paesi = sfoltisci(paesi, lambda p: (p["c"], p["p"]), 0.13, 16)
    cime = sfoltisci(cime, lambda p: p["q"], 0.16, 7)
    img = img.resize((NOUT, NOUT), Image.LANCZOS)
    os.makedirs(os.path.join(QUI, "base" + SUF), exist_ok=True)
    img.save(os.path.join(QUI, "base" + SUF, f"base_{lato}.jpg"), quality=82, optimize=True)
    k = NB // NDEM
    zd = z.reshape(NDEM, k, NDEM, k).mean(axis=(1, 3))
    zc = float(z[NB // 2 - 3:NB // 2 + 3, NB // 2 - 3:NB // 2 + 3].mean())
    json.dump({"n": NDEM, "dem": base64.b64encode(np.clip(zd, 0, 65535).astype("<u2").tobytes()).decode(),
               "zmin": round(float(z.min())), "zmax": round(float(z.max())), "quota_dem_centro": round(zc),
               "bosco_pct": round(float((cov == 10).mean()) * 100), "paesi": paesi, "cime": cime, "fiumi": fiumi, "lato_km": lato,
               "osm_errori": list(ERRORI)},
              open(os.path.join(QUI, "base" + SUF, f"base_{lato}.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"base {lato} km: quote {z.min():.0f}-{z.max():.0f} m, centro {zc:.0f} m, fiumi {fiumi}, paesi {len(paesi)}, cime {len(cime)}")


def main():
    lat, lon, quota = casa()
    for lato in LATI:
        ERRORI.clear()
        carta(lat, lon, quota, lato)


if __name__ == "__main__":
    main()

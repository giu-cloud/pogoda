"""Le tessere della carta di Pistrice: la grafica di Shift (tinte per quota, ombreggiatura, curve di livello, mare,
costa, fiumi) in tasselli 256 x 256 alla maniera delle carte del web (Web Mercator, livelli di zoom 10-14), cosi'
sul telefono si allarga con le dita senza sgranare. I nomi non sono nelle tessere: li scrive la pagina, sempre nitidi.
Si fa una volta: il terreno non cambia.

  LENS_DX=100 python3 pistrice/tessere.py      -> sito/pistrice/t/{z}/{x}/{y}.webp, sito/pistrice/luoghi.json"""
import json, math, os, sys
import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
from lens import calcola as C  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from scipy.ndimage import gaussian_filter, map_coordinates  # noqa: E402

USCITA = os.path.join(QUI, "..", "sito", "pistrice")
ZOOM = range(10, 15)
CURVE = {10: ((500, 0.40),), 11: ((200, 0.22), (1000, 0.45)), 12: ((100, 0.26), (500, 0.52)),
         13: ((50, 0.20), (250, 0.48)), 14: ((50, 0.24), (250, 0.50))}
FIUMI = {10: 1, 11: 2, 12: 2, 13: 3, 14: 4}


def x_di(lon, z):
    return (lon + 180) / 360 * 256 * 2 ** z


def y_di(lat, z):
    r = math.radians(lat)
    return (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * 256 * 2 ** z


def lat_di(y, z):
    return np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * y / (256 * 2 ** z)))))


def main():
    from rasterio.enums import Resampling
    si, ni, oi, ei = C.A.interno
    lat0 = (si + ni) / 2
    # il rilievo si legge su tutto quello che le tessere coprono al primo zoom (il piu' largo), cosi' ai bordi
    # delle tessere non restano strisce
    z0 = min(ZOOM)
    s = lat_di(np.array([(int(y_di(si - 0.03, z0) // 256) + 1) * 256]), z0)[0] - 0.01
    n = lat_di(np.array([int(y_di(ni + 0.03, z0) // 256) * 256]), z0)[0] + 0.01
    o = int(x_di(oi - 0.04, z0) // 256) * 256 / (256 * 2 ** z0) * 360 - 180 - 0.01
    e = (int(x_di(ei + 0.04, z0) // 256) + 1) * 256 / (256 * 2 ** z0) * 360 - 180 + 0.01
    print(f"rilievo letto su {s:.3f}-{n:.3f} N, {o:.3f}-{e:.3f} E")
    # rilievo a 30 m e copertura del suolo a 10 m, una volta sola
    ny30, nx30 = round((n - s) * 111190 / 30), round((e - o) * 111190 * math.cos(math.radians(lat0)) / 30)
    dem = np.maximum(C.mosaico(C.url_dem, 1, Resampling.bilinear, np.float32, (s, n, o, e), (ny30, nx30)), 0.0)
    ny10, nx10 = ny30 * 3, nx30 * 3
    try:
        cov = C.mosaico(C.url_cov, 3, Resampling.nearest, np.uint8, (s, n, o, e), (ny10, nx10))
    except Exception as ex:
        print("WorldCover non letto:", ex)
        cov = np.zeros((ny10, nx10), np.uint8)
    bosco = (cov == 10).astype(np.float32)
    citta = (cov == 50).astype(np.float32)
    acqua = ((cov == 80) | (cov == 0)).astype(np.float32)
    el = C.osm()
    print(f"terreno: {ny30}x{nx30} a 30 m, copertura {ny10}x{nx10}, OSM {len(el)} oggetti")
    rampa = [(0, (0xD3, 0xE0, 0xB8)), (120, (0xDE, 0xE5, 0xBE)), (300, (0xEA, 0xE3, 0xB6)), (500, (0xE3, 0xCF, 0xA2)),
             (700, (0xD3, 0xB9, 0x8C)), (900, (0xBF, 0x9F, 0x7C)), (1100, (0xAB, 0x8D, 0x73)), (1350, (0xA0, 0x86, 0x70))]
    qr = np.array([p[0] for p in rampa], np.float32)
    totale = 0
    dem_liscio = gaussian_filter(dem, 1.0)  # per l'ombreggiatura agli zoom alti: niente "puntinato" dei palazzi nel DSM
    for z in ZOOM:
        tx0, tx1 = int(x_di(oi - 0.04, z) // 256), int(x_di(ei + 0.04, z) // 256)
        ty0, ty1 = int(y_di(ni + 0.03, z) // 256), int(y_di(si - 0.03, z) // 256)
        W, H = (tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256
        px = tx0 * 256 + np.arange(W) + 0.5
        py = ty0 * 256 + np.arange(H) + 0.5
        lon = px / (256 * 2 ** z) * 360 - 180
        lat = lat_di(py, z)
        passo = 156543.03 * math.cos(math.radians(lat0)) / 2 ** z  # metri per pixel al suolo
        # indici nelle griglie in latitudine e longitudine
        r30 = (n - lat) / (n - s) * ny30 - 0.5
        c30 = (lon - o) / (e - o) * nx30 - 0.5
        R, Cc = np.meshgrid(r30, c30, indexing="ij")
        h = map_coordinates(dem, [R, Cc], order=3, mode="nearest").astype(np.float32)
        h = np.maximum(h, 0.0)
        sig = max(0.0, passo / 10.0 / 2.0 - 0.5)

        def frazione(a):
            b = gaussian_filter(a, sig) if sig > 0.3 else a
            return map_coordinates(b, [R * 3 + 1, Cc * 3 + 1], order=1, mode="nearest").astype(np.float32)
        fb, fc, fa = frazione(bosco), frazione(citta), frazione(acqua)
        rgb = np.stack([np.interp(h, qr, [p[1][i] for p in rampa]) for i in range(3)], axis=-1).astype(np.float32)
        for f, col, forza in ((fb, (126, 164, 110), 0.42), (fc, (214, 186, 176), 0.55)):
            rgb += (np.array(col, np.float32) - rgb) * (f * forza)[..., None]
        hs = h if z <= 12 else np.maximum(map_coordinates(dem_liscio, [R, Cc], order=3, mode="nearest"), 0.0)
        esag = {10: 2.4, 11: 2.4, 12: 2.2, 13: 1.8, 14: 1.5}[z]
        gy, gx = np.gradient(hs, passo)
        dzdx, dzdy = gx * esag, -gy * esag
        rel = np.clip((0.5 * dzdx - 0.5 * dzdy + 0.7071) / np.sqrt(dzdx ** 2 + dzdy ** 2 + 1.0) / 0.7071, 0.0, 1.45)
        rgb *= np.clip(0.52 + 0.48 * rel, 0.55, 1.16)[..., None]
        inchiostro = np.array((0x7A, 0x5A, 0x3C), np.float32)
        for intervallo, forza in CURVE[z]:
            liv = np.floor(h / intervallo)
            bordo = np.zeros(liv.shape, bool)
            bordo[:-1, :] |= liv[:-1, :] != liv[1:, :]
            bordo[:, :-1] |= liv[:, :-1] != liv[:, 1:]
            bordo &= h > 1
            rgb[bordo] = rgb[bordo] * (1 - forza) + inchiostro * forza
        mare = (h <= 0.5) & (fa > 0.5)
        rgb[mare] = (0xCF, 0xE3, 0xEC)
        costa = np.zeros(mare.shape, bool)
        costa[:-1, :] |= mare[:-1, :] != mare[1:, :]
        costa[:, :-1] |= mare[:, :-1] != mare[:, 1:]
        rgb[costa] = (0x8E, 0xA2, 0xB2)
        img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img)
        for x in el:
            if x.get("type") == "way" and x.get("geometry"):
                d.line([(x_di(g["lon"], z) - tx0 * 256, y_di(g["lat"], z) - ty0 * 256) for g in x["geometry"]],
                       fill=(66, 128, 204), width=FIUMI[z], joint="curve")
        n_t = 0
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                cart = os.path.join(USCITA, "t", str(z), str(tx))
                os.makedirs(cart, exist_ok=True)
                img.crop(((tx - tx0) * 256, (ty - ty0) * 256, (tx - tx0 + 1) * 256, (ty - ty0 + 1) * 256)).save(
                    os.path.join(cart, f"{ty}.webp"), "WEBP", quality=78, method=6)
                n_t += 1
        totale += n_t
        print(f"zoom {z}: {W}x{H} px, {n_t} tessere, {passo:.1f} m/px")
    # linea di costa vettoriale (sopra i colori del vento, perche' il posto si riconosca sempre)
    try:
        import contourpy
        fa30 = acqua.reshape(ny30, 3, nx30, 3).mean(axis=(1, 3))
        campo_m = np.where(dem <= 0.5, fa30, 0.0)
        linee = []
        for ln in contourpy.contour_generator(z=gaussian_filter(campo_m, 0.6)).lines(0.5):
            if len(ln) < 6:
                continue
            # contourpy restituisce (colonna, riga)
            la_ = n - (ln[:, 1] + 0.5) / ny30 * (n - s)
            lo_ = o + (ln[:, 0] + 0.5) / nx30 * (e - o)
            dentro = (la_ > si - 0.05) & (la_ < ni + 0.05) & (lo_ > oi - 0.06) & (lo_ < ei + 0.06)
            if dentro.sum() < 4:
                continue
            linee.append([[round(float(a_), 5), round(float(b_), 5)] for a_, b_ in zip(la_[::2], lo_[::2])])
        json.dump(linee, open(os.path.join(USCITA, "costa.json"), "w"), separators=(",", ":"))
        print("costa:", len(linee), "linee,", sum(len(x) for x in linee), "punti")
    except Exception as ex:
        print("costa non fatta:", ex)
    # i nomi, con latitudine e longitudine, in ordine di importanza
    luoghi = []
    for nome, fx, fy, pri, tipo in C.luoghi(el):
        si, ni, oi, ei = C.A.interno
        luoghi.append([nome, round(ni - fy * (ni - si), 5), round(oi + fx * (ei - oi), 5), pri, tipo])
    json.dump({"luoghi": luoghi, "limiti": [si, ni, oi, ei], "zoom": [min(ZOOM), max(ZOOM)]},
              open(os.path.join(USCITA, "luoghi.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    print("tessere:", totale, "· nomi:", len(luoghi))


if __name__ == "__main__":
    main()

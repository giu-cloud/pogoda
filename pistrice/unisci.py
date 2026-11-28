"""Pistrice Sailing Weather Lab: unisce i due calcoli di Lens (ECMWF e ICON-2I, ognuno con il suo Lens 2) come il motore
0.59.1: forza 0,7 ECMWF + 0,3 ICON-2I (lens/analoghi_25_11.md), direzione con 0,3 ECMWF + 0,7 ICON-2I
(LensRadar.PESI_DIREZIONE, decisione 13 del 27/11). Pioggia e temporali da ICON-2I. Poi scrive la pagina.

  python3 pistrice/unisci.py ecmwf.json icon.json     -> pistrice/uscita/index.html"""
import base64, gzip, json, os, sys
import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__))
FORZA = (0.7, 0.3)
DIREZIONE = (0.3, 0.7)


def carica(p):
    if not os.path.exists(p):
        return None
    x = json.load(open(p))
    x["dati"]["_P"] = json.loads(gzip.decompress(base64.b64decode(x["dati"]["gz"])))
    return x


def campi(o, n):
    v = np.frombuffer(base64.b64decode(o["v"]), np.uint8).astype(float)[:n] / 4
    g = np.frombuffer(base64.b64decode(o["g"]), np.uint8).astype(float)[:n] / 4
    a = np.frombuffer(base64.b64decode(o["d"]), np.uint8).astype(float)[:n] / 256 * 2 * np.pi
    return v, g, a


def main():
    e, i = carica(sys.argv[1]), carica(sys.argv[2])
    if not e and not i:
        sys.exit("nessun calcolo da unire")
    base = i or e
    d = base["dati"]
    n = d["nx"] * d["ny"]
    ore_out = []
    if e and i:
        oe = {o["t"]: o for o in e["dati"]["_P"]["ore"]}
        for o in i["dati"]["_P"]["ore"]:
            if o["t"] not in oe:
                continue
            ve, ge, ae = campi(oe[o["t"]], n)
            vi, gi, ai = campi(o, n)
            v = FORZA[0] * ve + FORZA[1] * vi
            g = np.maximum(FORZA[0] * ge + FORZA[1] * gi, v)
            u = DIREZIONE[0] * np.sin(ae) * ve + DIREZIONE[1] * np.sin(ai) * vi
            w = DIREZIONE[0] * np.cos(ae) * ve + DIREZIONE[1] * np.cos(ai) * vi
            ore_out.append((o, v, g, np.degrees(np.arctan2(u, w)) % 360))
        d["nome_modello"] = "ECMWF e ICON-2I"
        d["lens2"] = bool(e["dati"].get("lens2") or i["dati"].get("lens2"))
        print(f"insieme: {len(ore_out)} ore comuni")
    if not ore_out:
        for o in d["_P"]["ore"]:
            v, g, a = campi(o, n)
            ore_out.append((o, v, g, np.degrees(a) % 360))
        print("un solo calcolo:", d.get("nome_modello"))
    # campi compatti: mezzi nodi e 128 direzioni, differenze ora per ora (si comprimono molto meglio)
    blocchi = {"v": [], "g": [], "d": []}
    meta = []
    for o, v, g, dd in ore_out:
        blocchi["v"].append(np.clip(np.round(v * 2), 0, 255).astype(np.int64))
        blocchi["g"].append(np.clip(np.round(g * 2), 0, 255).astype(np.int64))
        blocchi["d"].append(np.round(dd / 360 * 128).astype(np.int64) % 128)
        meta.append({k: o.get(k) for k in ("t", "a2", "q", "pr", "ca", "fr")})
    bin_ = []
    for k in ("v", "g", "d"):
        a = np.stack(blocchi[k])
        bin_.append((np.diff(np.concatenate([np.zeros((1, n), np.int64), a]), axis=0) % 256).astype(np.uint8).ravel())
    pacco = {"ore": meta, "mare": d["_P"]["mare"]}
    onde = None
    try:
        sys.path.insert(0, QUI)
        from onde import leggi
        onde = leggi(d["interno"], [m["t"] for m in meta])
    except Exception as ex:
        print("onde non lette:", ex)
    dati = {k: d[k] for k in ("nx", "ny", "dx", "m", "NX", "NY", "gx", "gy", "interno", "generato") if k in d}
    dati.update({"modello": d.get("nome_modello") or d.get("modello"), "lens2": bool(d.get("lens2")), "onde": onde,
                 "gz": base64.b64encode(gzip.compress(json.dumps(pacco, separators=(",", ":")).encode(), 9)).decode(),
                 "bin": base64.b64encode(gzip.compress(np.concatenate(bin_).tobytes(), 9)).decode()})
    sys.path.insert(0, QUI)
    from pagina import pagina
    usc = os.path.join(QUI, "uscita")
    os.makedirs(usc, exist_ok=True)
    open(os.path.join(usc, "index.html"), "w", encoding="utf-8").write(pagina(dati))
    print("pagina:", os.path.getsize(os.path.join(usc, "index.html")) // 1024, "KB")


if __name__ == "__main__":
    main()

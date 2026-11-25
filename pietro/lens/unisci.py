"""L'insieme di Lens 2, come nel laboratorio (lens/analoghi_25_11.md): ogni modello corretto con la sua libreria del
radar, poi forza = 0,7 ECMWF + 0,3 ICON-2I e direzione = media dei vettori con gli stessi pesi. Pioggia e temporali da
ICON-2I, che ha il dettaglio. Se uno dei due calcoli manca, la pagina si fa con l'altro.

  python3 lens/unisci.py ecmwf.json icon.json"""
import base64, gzip, json, os, sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PESI = (0.7, 0.3)


def carica(p):
    if not os.path.exists(p):
        return None
    x = json.load(open(p))
    d = x["dati"]
    d["_P"] = json.loads(gzip.decompress(base64.b64decode(d["gz"])))
    return x


def campi(o, n):
    v = np.frombuffer(base64.b64decode(o["v"]), np.uint8).astype(float)[:n] / 4
    g = np.frombuffer(base64.b64decode(o["g"]), np.uint8).astype(float)[:n] / 4
    a = np.frombuffer(base64.b64decode(o["d"]), np.uint8).astype(float)[:n] / 256 * 2 * np.pi
    return v, g, -v * np.sin(a), -v * np.cos(a)


def b64(a):
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def main():
    e, i = carica(sys.argv[1]), carica(sys.argv[2])
    if not e and not i:
        sys.exit("nessun calcolo da unire")
    base = i or e
    d = base["dati"]
    if e and i:
        de, di = e["dati"], i["dati"]
        assert (de["nx"], de["ny"]) == (di["nx"], di["ny"]), "griglie diverse"
        n = di["nx"] * di["ny"]
        oe = {o["t"]: o for o in de["_P"]["ore"]}
        ore = []
        for o in di["_P"]["ore"]:
            if o["t"] not in oe:
                continue
            ve, ge, ue, we = campi(oe[o["t"]], n)
            vi, gi, ui, wi = campi(o, n)
            v = PESI[0] * ve + PESI[1] * vi
            g = PESI[0] * ge + PESI[1] * gi
            u, w = PESI[0] * ue + PESI[1] * ui, PESI[0] * we + PESI[1] * wi
            dd = (np.degrees(np.arctan2(-u, -w)) % 360)
            o2 = dict(o)
            o2["v"] = b64(np.clip(np.round(v * 4), 0, 255).astype(np.uint8))
            o2["g"] = b64(np.clip(np.round(np.maximum(g, v) * 4), 0, 255).astype(np.uint8))
            o2["d"] = b64(np.round(dd / 360 * 256).astype(np.int64).astype(np.uint8))
            o2.pop("mv", None); o2.pop("md", None)
            ore.append(o2)
        if ore:
            di["_P"]["ore"] = ore
            di["n_ore"] = len(ore)
            di["nome_modello"] = "ECMWF e ICON-2I (insieme 0,7 / 0,3)"
            di["lens2"] = bool(de.get("lens2") or di.get("lens2"))
            d = di
            print(f"insieme: {len(ore)} ore comuni")
        else:
            print("nessuna ora in comune: solo ICON-2I")
    else:
        print("un solo calcolo:", d.get("nome_modello"))
    P = d.pop("_P")
    for o in P["ore"]:
        o.pop("mv", None); o.pop("md", None)
    d["gz"] = base64.b64encode(gzip.compress(json.dumps(P, separators=(",", ":")).encode(), 9)).decode()
    for x in (e, i):
        if x:
            x["dati"].pop("_P", None)
    from lens.pagina import pagina
    usc = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uscita")
    os.makedirs(usc, exist_ok=True)
    open(os.path.join(usc, "pagina.html"), "w", encoding="utf-8").write(pagina(d, base["carta"], "image/webp"))
    print("pagina:", os.path.getsize(os.path.join(usc, "pagina.html")) // 1024, "KB")


if __name__ == "__main__":
    main()

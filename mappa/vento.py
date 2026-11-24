"""Atlante del vento: come il rilievo vero piega, frena e accelera il vento, per ogni carta.

E' il metodo Lens (conservazione della massa in 3D sul terreno, come WindNinja) usato una volta per tutte.
L'aggiustamento e' lineare: con la stabilita' fissata, la risposta del rilievo a un vento qualsiasi e' la
combinazione delle risposte a un vento unitario da ovest (verso est) e da sud (verso nord). Quindi si calcolano
qui due risposte per tre classi di stabilita' (neutra, stabile, molto stabile), e la pagina le combina ora per ora
con il vento del modello. Il calcolo pesante si fa una volta, quando cambia la carta di base.

Scrive mappa/base*/vento_<lato>.json: per ogni classe, le componenti est e nord del vento a 10 m dal suolo
per un vento unitario verso est e verso nord, in centesimi, su una griglia di 100 x 100."""
import base64, json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from comune.base import SUF
from mappa.geo import LATI
from mappa.solutore import aggiusta, al_suolo

QUI = os.path.dirname(os.path.abspath(__file__))
CLASSI = [1.0, 0.25, 0.05]  # alfa2 = Froude^2: neutro, stabile, molto stabile
NV = 100  # lato della griglia salvata
Z0_RIF = 0.25  # rugosita' media a cui si riferisce il vento a 10 m del modello


def livelli(h, dx):
    dz0 = float(np.clip(dx / 8, 15, 50))
    fondo = np.floor(h.min() / dz0) * dz0 - 2 * dz0
    dz = []
    while fondo + sum(dz) < h.max() + 300:
        dz.append(dz0)
    while fondo + sum(dz) < h.max() + 3000:
        dz.append(dz[-1] * 1.3)
    dz = np.array(dz)
    zf = fondo + np.concatenate([[0.0], np.cumsum(dz)])
    return dz, 0.5 * (zf[:-1] + zf[1:])


def iniziale(h, z0, zc):
    """Vento unitario a 10 m su un suolo di rugosita' media, portato in quota con il profilo logaritmico fino a 100 m
    dal suolo (con la rugosita' vera di ogni punto sotto i 100 m), costante sopra."""
    u100 = np.log(100 / Z0_RIF) / np.log(10 / Z0_RIF)
    agl = np.clip(zc[:, None, None] - h[None], 2.0, 100.0)
    return (u100 * np.log(np.maximum(agl, z0[None] * 1.5) / z0[None]) / np.log(100 / z0[None])).astype(np.float32)


def ricampiona(a, n):
    m = a.shape[0]
    x = (np.arange(n) + 0.5) * m / n - 0.5
    i0 = np.clip(np.floor(x).astype(int), 0, m - 2)
    w = np.clip(x - i0, 0, 1)
    r = a[i0] * (1 - w)[:, None] + a[i0 + 1] * w[:, None]
    return r[:, i0] * (1 - w)[None] + r[:, i0 + 1] * w[None]


def atlante(lato):
    cart = os.path.join(QUI, "base" + SUF)
    b = json.load(open(os.path.join(cart, f"base_{lato}.json")))
    n = b["n"]
    h = np.frombuffer(base64.b64decode(b["dem"]), "<u2").reshape(n, n).astype(np.float64)
    try:
        z0 = np.load(os.path.join(cart, f"rug_{lato}.npy")).astype(np.float64)
    except FileNotFoundError:
        z0 = np.full((n, n), Z0_RIF)
    z0 = np.clip(z0, 0.0003, 1.0)
    dx = lato * 1000 / n
    dz, zc = livelli(h, dx)
    prof = iniziale(h, z0, zc)
    zero = np.zeros_like(prof)
    campi, memoria, t0 = [], {}, time.time()
    for a2 in CLASSI:
        for u0, v0 in ((prof, zero), (zero, prof)):
            u, v, w, aria, div = aggiusta(h, u0, v0, dx, dz, zc, alfa2=a2, tol=1e-5, memoria=memoria)
            us, vs = al_suolo(u, v, aria, h, zc, z0)
            campi += [ricampiona(us, NV), ricampiona(vs, NV)]
    rilievo = float(np.percentile(h, 98) - np.percentile(h, 2))
    q = np.clip(np.round(np.stack(campi) * 100), -32000, 32000).astype("<i2")
    out = {"n": NV, "classi": CLASSI, "rilievo": round(rilievo), "f": base64.b64encode(q.tobytes()).decode()}
    json.dump(out, open(os.path.join(cart, f"vento_{lato}.json"), "w"), separators=(",", ":"))
    sp = np.hypot(campi[0], campi[1])
    print(f"vento {lato} km: {len(zc)} livelli, dx {dx:.0f} m, rilievo {rilievo:.0f} m, "
          f"risposta a vento unitario (neutro) {sp.min():.2f}-{sp.max():.2f}, {time.time() - t0:.0f} s")


def main():
    for lato in LATI:
        atlante(lato)


if __name__ == "__main__":
    main()

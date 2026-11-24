"""Vento sul rilievo vero con un modello tridimensionale a conservazione di massa.

Idea (Sherman 1978, la stessa di WindNinja): si parte dal vento del modello meteo interpolato (campo iniziale),
che attraversa le montagne come se non ci fossero, e si cerca il campo piu' vicino possibile a quello che pero'
non attraversi il terreno e non crei ne' distrugga aria (divergenza nulla). "Vicino" pesa in modo diverso gli
spostamenti orizzontali e verticali: con aria stabile salire costa caro e il flusso gira attorno ai rilievi,
con aria instabile scavalca. Il rapporto e' alfa2 (1 = neutro, minore di 1 = stabile).

Griglia cartesiana sfalsata: le celle sotto il terreno sono solide. Si risolve un'equazione di Poisson
per il moltiplicatore lambda con un multigrid algebrico. Quello che questo modello NON fa: scie, vortici e
ricircoli sottovento, che nascono dall'inerzia e dall'attrito. Quelli sono stimati a parte (vedi scia())."""
import numpy as np
import scipy.sparse as sp


def livelli():
    """Spessori dei livelli: 20 m dal mare fino a 1200 m (sopra Monte Cuccio), poi sempre piu' larghi fino a oltre 3000 m."""
    dz = [20.0] * 60
    while sum(dz) < 3200:
        dz.append(dz[-1] * 1.3)
    dz = np.array(dz)
    zf = np.concatenate([[0.0], np.cumsum(dz)])
    return dz, 0.5 * (zf[:-1] + zf[1:])


def aggiusta(h, u0, v0, dx, dz, zc, alfa2=1.0, tol=1e-5, memoria=None):
    """alfa2: un numero solo, oppure un valore per ogni livello (stabilita' diversa in basso e in alto)."""
    return _aggiusta(h, u0, v0, dx, dz, zc, np.broadcast_to(np.asarray(alfa2, dtype=float), dz.shape).copy(), tol, memoria)


def _aggiusta(h, u0, v0, dx, dz, zc, alfa2, tol, memoria):
    """h: terreno (ny, nx) in metri, riga 0 a nord. u0 verso est, v0 verso NORD: campo iniziale al centro delle celle (nz, ny, nx).
    Dentro il calcolo l'asse delle righe va verso sud, quindi v si cambia di segno all'ingresso e all'uscita.
    Ritorna u, v, w al centro delle celle, la maschera delle celle d'aria e la divergenza residua."""
    import pyamg
    nz, ny, nx = u0.shape
    aria = zc[:, None, None] > h[None, :, :]
    idx = -np.ones(aria.shape, dtype=np.int64)
    n = int(aria.sum())
    idx[aria] = np.arange(n)
    dzk = dz[:, None, None] * np.ones(aria.shape)
    # velocita' iniziali sulle facce (zero se una delle due celle e' solida)
    uf = np.zeros((nz, ny, nx + 1)); vf = np.zeros((nz, ny + 1, nx)); wf = np.zeros((nz + 1, ny, nx))
    ua, va = np.where(aria, u0, 0.0), np.where(aria, -v0, 0.0)
    dentro = aria[:, :, 1:] & aria[:, :, :-1]
    uf[:, :, 1:-1] = np.where(dentro, 0.5 * (ua[:, :, 1:] + ua[:, :, :-1]), 0.0)
    uf[:, :, 0], uf[:, :, -1] = ua[:, :, 0], ua[:, :, -1]
    dentro = aria[:, 1:, :] & aria[:, :-1, :]
    vf[:, 1:-1, :] = np.where(dentro, 0.5 * (va[:, 1:, :] + va[:, :-1, :]), 0.0)
    vf[:, 0, :], vf[:, -1, :] = va[:, 0, :], va[:, -1, :]
    div = (uf[:, :, 1:] - uf[:, :, :-1]) / dx + (vf[:, 1:, :] - vf[:, :-1, :]) / dx + (wf[1:] - wf[:-1]) / dzk
    # matrice (simmetrica: ogni riga e' moltiplicata per lo spessore della cella)
    ch = 0.5
    cvl = 0.5 * alfa2                    # peso verticale per livello
    cvf = 0.5 * (cvl[1:] + cvl[:-1])     # sulle facce tra un livello e quello sopra
    righe, colonne, valori = [], [], []
    diag = np.zeros(n)
    def coppie(a, b, coef):
        ok = (a >= 0) & (b >= 0)
        ia, ib, c = a[ok], b[ok], coef[ok]
        righe.extend([ia, ib]); colonne.extend([ib, ia]); valori.extend([-c, -c])
        np.add.at(diag, ia, c); np.add.at(diag, ib, c)
    coppie(idx[:, :, :-1], idx[:, :, 1:], (ch * dzk / dx ** 2)[:, :, 1:])
    coppie(idx[:, :-1, :], idx[:, 1:, :], (ch * dzk / dx ** 2)[:, 1:, :])
    dzc = 0.5 * (dz[1:] + dz[:-1])
    coppie(idx[:-1], idx[1:], (cvf / dzc)[:, None, None] * np.ones((nz - 1, ny, nx)))
    # bordi aperti (lambda = 0 fuori): lati e cima
    for lato in (idx[:, :, 0], idx[:, :, -1], idx[:, 0, :], idx[:, -1, :]):
        k = np.broadcast_to(dz[:, None], lato.shape)
        ok = lato >= 0
        np.add.at(diag, lato[ok], ch * k[ok] / dx ** 2 * 2.0)
    cima = idx[-1]
    np.add.at(diag, cima[cima >= 0], cvl[-1] / (dz[-1] * 0.5))
    A = sp.coo_matrix((np.concatenate(valori), (np.concatenate(righe), np.concatenate(colonne))), shape=(n, n)).tocsr()
    A = A + sp.diags(diag)
    b = -(div * dzk)[aria]
    # la matrice dipende solo dal terreno e da alfa2: se alfa2 non cambia si riusa la gerarchia gia' costruita,
    # e si parte dalla soluzione dell'ora prima
    memoria = memoria if memoria is not None else {}
    chiave = tuple(np.round(alfa2, 4))
    if memoria.get("alfa2") != chiave:
        memoria.clear()
        memoria["alfa2"] = chiave
        memoria["ml"] = pyamg.smoothed_aggregation_solver(A, max_coarse=500)
    lam_v = memoria["ml"].solve(b, x0=memoria.get("x"), tol=tol, accel="cg", maxiter=200)
    memoria["x"] = lam_v
    lam = np.zeros(aria.shape); lam[aria] = lam_v
    # correzione delle facce: du = -ch * d(lambda)/dx (segno coerente con la matrice positiva)
    def grad(a_dopo, a_prima, l_dopo, l_prima, passo):
        return np.where(a_dopo & a_prima, (l_dopo - l_prima) / passo, 0.0)
    uf[:, :, 1:-1] -= ch * grad(aria[:, :, 1:], aria[:, :, :-1], lam[:, :, 1:], lam[:, :, :-1], dx)
    uf[:, :, 0] -= ch * np.where(aria[:, :, 0], lam[:, :, 0] / (dx / 2), 0.0)
    uf[:, :, -1] -= ch * np.where(aria[:, :, -1], -lam[:, :, -1] / (dx / 2), 0.0)
    vf[:, 1:-1, :] -= ch * grad(aria[:, 1:, :], aria[:, :-1, :], lam[:, 1:, :], lam[:, :-1, :], dx)
    vf[:, 0, :] -= ch * np.where(aria[:, 0, :], lam[:, 0, :] / (dx / 2), 0.0)
    vf[:, -1, :] -= ch * np.where(aria[:, -1, :], -lam[:, -1, :] / (dx / 2), 0.0)
    wf[1:-1] -= cvf[:, None, None] * grad(aria[1:], aria[:-1], lam[1:], lam[:-1], dzc[:, None, None])
    wf[-1] -= cvl[-1] * np.where(aria[-1], -lam[-1] / (dz[-1] / 2), 0.0)
    div2 = (uf[:, :, 1:] - uf[:, :, :-1]) / dx + (vf[:, 1:, :] - vf[:, :-1, :]) / dx + (wf[1:] - wf[:-1]) / dzk
    u = 0.5 * (uf[:, :, 1:] + uf[:, :, :-1]); v = -0.5 * (vf[:, 1:, :] + vf[:, :-1, :]); w = 0.5 * (wf[1:] + wf[:-1])
    return u, v, w, aria, (float(np.abs(div[aria]).mean()), float(np.abs(div2[aria]).mean()))


def al_suolo(u, v, aria, h, zc, z0, quota=10.0):
    """Vento a 10 m dal suolo: si prende la cella d'aria piu' bassa di ogni colonna e si riporta a 10 m
    con il profilo logaritmico della rugosita' locale."""
    k0 = np.argmax(aria, axis=0)
    jj, ii = np.indices(h.shape)
    # media delle due celle piu' basse: attenua il gradino della griglia a scalini
    k1 = np.minimum(k0 + 1, aria.shape[0] - 1)
    us, vs = 0.5 * (u[k0, jj, ii] + u[k1, jj, ii]), 0.5 * (v[k0, jj, ii] + v[k1, jj, ii])
    agl = np.maximum(0.5 * (zc[k0] + zc[k1]) - h, 6.0)
    f = np.log(quota / z0) / np.log(np.maximum(agl, quota) / z0)
    return us * f, vs * f


def scia(h, us, vs, dx, froude, portata_km=3.0):
    """Ridosso sottovento (parte NON risolta dalla conservazione di massa): per ogni punto si guarda
    sopravvento lungo il vento locale e si misura l'angolo sotto cui si vede il rilievo piu' alto (parametro
    Sx di Winstral). Con aria stabile e vento debole la scia si allunga. Ritorna il fattore di riduzione
    (1 = nessun ridosso) e l'angolo in gradi. Le costanti sono ipotesi da tarare con gli anemometri."""
    from scipy.ndimage import map_coordinates
    ny, nx = h.shape
    vel = np.hypot(us, vs) + 1e-6
    ex, ey = us / vel, vs / vel
    froude = froude if np.isfinite(froude) else 1.0
    portata = portata_km * 1000.0 * float(np.clip(1.0 / max(froude, 0.2), 0.7, 3.0))
    jj, ii = np.indices(h.shape, dtype=float)
    sx = np.full(h.shape, -90.0)
    for d in np.arange(dx, portata + dx, dx):
        # sopravvento: verso ovest se il vento va a est (colonne), verso sud se va a nord (righe crescenti)
        hm = map_coordinates(h, [jj + ey * d / dx, ii - ex * d / dx], order=1, mode="nearest")
        sx = np.maximum(sx, np.degrees(np.arctan2(hm - (h + 10.0), d)))
    fattore = 1.0 - 0.65 * np.clip((sx - 3.0) / 14.0, 0.0, 1.0)
    return fattore, sx


def costa(mare, z0, us, vs, dx, c=0.75, zb=200.0, portata=5000.0, z0s=0.0002):
    """Passaggio terra-mare (strato limite interno). Il vento che arriva da terra e' frenato dalla rugosita'
    (campagna, bosco, citta'); sul mare riaccelera man mano che sotto si forma uno strato nuovo, liscio,
    che cresce con la distanza dalla costa: delta = c * z0^0,2 * x^0,8 (Elliott). Quando delta arriva alla
    quota di raccordo zb il vento e' tornato quello del mare aperto. c dipende dalla stabilita': con aria
    stabile lo strato cresce piano e la fascia di vento debole lungo costa si allunga.
    Ritorna il fattore sul vento a 10 m (1 = nessun effetto), la distanza sopravvento dalla costa,
    la frazione di recupero dello strato nuovo (0 sulla costa, 1 quando e' completo) e la rugosita' della terra sopravvento."""
    from scipy.ndimage import map_coordinates
    vel = np.hypot(us, vs) + 1e-6
    ex, ey = us / vel, vs / vel
    jj, ii = np.indices(mare.shape, dtype=float)
    terra = (~mare).astype(float)
    x = np.zeros(mare.shape)
    z0l = np.zeros(mare.shape)
    trovato = np.zeros(mare.shape, dtype=bool)
    for d in np.arange(dx, portata + dx, dx):
        r, cc = jj + ey * d / dx, ii - ex * d / dx
        t = map_coordinates(terra, [r, cc], order=0, mode="nearest") > 0.5
        nuovo = t & ~trovato & mare
        if nuovo.any():
            zz = sum(map_coordinates(z0, [r + ey * k, cc - ex * k], order=0, mode="nearest") for k in range(4)) / 4
            x[nuovo] = d
            z0l[nuovo] = zz[nuovo]
            trovato |= nuovo
    f = np.ones(mare.shape)
    m = trovato
    zl = np.maximum(z0l[m], 0.01)
    delta = np.clip(c * np.maximum(zl, z0s) ** 0.2 * x[m] ** 0.8, 10.0, zb)
    sopra = np.log(delta / zl) / np.log(zb / zl)          # vento di terra all'altezza delta, rispetto alla quota di raccordo
    equilibrio = np.log(10.0 / z0s) / np.log(zb / z0s)  # vento a 10 m sul mare aperto, stessa scala
    f[m] = np.minimum(1.0, sopra * np.log(10.0 / z0s) / np.log(delta / z0s) / equilibrio)
    rec = np.ones(mare.shape)
    rec[m] = (delta - 10.0) / (zb - 10.0)
    return f, np.where(m, x, np.inf), rec, z0l


def raffiche(vel, mare, z0, rec, z0l, fattore_scia, ti_mare, picco=3.0):
    """Raffica a 10 m dall'intensita' di turbolenza locale: 1/ln(10/z0) per lo strato superficiale neutro.
    In mare, vicino alla costa, la turbolenza portata da terra si smorza piu' piano del vento medio
    (radice della frazione non ancora recuperata); nella scia dei rilievi la turbolenza cresce.
    ti_mare: turbolenza in mare aperto, tarata sul rapporto raffica/vento del modello al largo;
    picco: fattore di picco della raffica di 3 secondi (valore classico, circa 3)."""
    ti = np.where(mare, ti_mare, 1.0 / np.log(10.0 / np.maximum(z0, 0.001)))
    ti_terra = 1.0 / np.log(10.0 / np.maximum(z0l, 0.01))
    da_terra = mare & (rec < 1.0)
    ti[da_terra] = ti_mare + (ti_terra[da_terra] - ti_mare) * np.sqrt(1.0 - rec[da_terra])
    ti = ti + 0.25 * (1.0 - fattore_scia)
    return vel * np.minimum(1.0 + picco * ti, 2.6), ti

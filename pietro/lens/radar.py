"""Lens 2: la correzione della forza del vento imparata dal radar dei Sentinel-1 (librerie LRA1 del laboratorio Lens,
giu-cloud/lens, release librerie-lra1). Lettura e calcolo come in banco/strumenti/libreria_radar.py e nel motore
Kotlin (LensRadar): a ogni ora le 25 scene del radar piu' simili alla situazione prevista, media pesata del rapporto
vero/modello, cella per cella a 1 km. La direzione non cambia. Fuori dalle celle (a terra e oltre l'area) il fattore e' 1."""
import gzip, struct
import numpy as np

LARGO_KM = 8.0  # come nella costruzione della libreria: oltre questa distanza dalla terra la cella conta come largo


class Libreria:
    def __init__(self, path):
        d = gzip.open(path, "rb").read(); o = 0

        def rd(fmt):
            nonlocal o
            v = struct.unpack_from(fmt, d, o); o += struct.calcsize(fmt); return v

        def rs():
            nonlocal o
            n, = rd("<h"); s = d[o:o + n].decode("utf-8"); o += n; return s

        def arr(dt, n):
            nonlocal o
            a = np.frombuffer(d, dtype=dt, count=n, offset=o); o += a.nbytes; return a
        assert d[:4] == b"LRA1"; o = 4
        self.versione, = rd("<i"); self.area = rs(); self.modello = rs()
        self.lat0, self.lon0, self.dlat, self.dlon, self.ny, self.nx = rd("<4d2i")
        self.nc, = rd("<i"); self.celle = arr("<i4", self.nc); self.dist = arr("<f4", self.nc)
        self.K, self.k_an, self.sd_v, self.sd_925, self.sd_ora, self.vmin, self.wbar = rd("<7f")
        self.coef = arr("<f4", 5 * self.nc).reshape(5, self.nc)
        self.ns, = rd("<i"); self.t = arr("<i8", self.ns)
        self.a0, self.b0, self.a925, self.b925 = (arr("<f4", self.ns) for _ in range(4))
        self.sera = arr("u1", self.ns)
        Mq = arr("u1", self.ns * self.nc).reshape(self.ns, self.nc); Qq = arr("u1", self.ns * self.nc).reshape(self.ns, self.nc)
        M = np.where(Mq < 255, Mq.astype("f4") * 0.1, np.nan)
        Q = np.where(Qq < 255, np.exp((Qq.astype("f4") - 128) / 64.0), np.nan)
        ok = np.isfinite(M) & np.isfinite(Q) & (M > self.vmin)
        self.ww = np.where(ok, M * M, 0.0).astype("f8")
        self.wy = np.where(ok, Q * M * M, 0.0).astype("f8")
        self.X = np.stack([self.a0 / self.sd_v, self.b0 / self.sd_v, self.sera / self.sd_ora,
                           self.a925 / self.sd_925, self.b925 / self.sd_925], axis=1).astype("f8")
        j, i = self.celle // self.nx, self.celle % self.nx
        self.lat = self.lat0 + j * self.dlat
        self.lon = self.lon0 + i * self.dlon

    def fattore(self, a0, b0, a925, b925, sera, dir_celle):
        x = np.array([a0 / self.sd_v, b0 / self.sd_v, sera / self.sd_ora, a925 / self.sd_925, b925 / self.sd_925])
        d2 = np.sum((self.X - x) ** 2, axis=1)
        K = min(int(self.K), self.ns)
        idx = np.argsort(d2, kind="stable")[:K]
        med = np.median(d2[idx])
        pk = np.exp(-0.5 * d2[idx] / max(med, 1e-6))
        th = np.radians(dir_celle)
        base = (self.coef[0] + self.coef[1] * np.cos(th) + self.coef[2] * np.sin(th) + self.coef[3] * np.cos(2 * th)
                + self.coef[4] * np.sin(2 * th))
        lam = self.k_an * self.wbar
        return (pk @ self.wy[idx] + lam * base) / (pk @ self.ww[idx] + lam)


def provenienza(u, v):
    return (np.degrees(np.arctan2(-u, -v)) + 360) % 360


def relativo_a_lens(lib, G, sp_celle, vel_fine, mare_fine, lat_fine, lon_fine):
    """Lens 0.57 (Giano, 25/11): Lens sotto ha il rilievo pieno, e la libreria e' imparata sul modello senza rilievo, quindi
    il suo fattore conterebbe due volte le ombre e i getti che il radar vede. Ogni cella si divide per quanto Lens, in
    media sulla cella, ha gia' cambiato il vento del modello: g' = g / (media di Lens nella cella / modello nella cella).
    Sulla cella del radar Lens corretto torna in media al radar; dentro resta il disegno fine di Lens. Come
    LensRadar.relativoALens del motore di Shift."""
    LA, LO = np.meshgrid(lat_fine, lon_fine, indexing="ij")
    jj = np.rint((LA - lib.lat0) / lib.dlat).astype(int); ii = np.rint((LO - lib.lon0) / lib.dlon).astype(int)
    ok = mare_fine & np.isfinite(vel_fine) & (jj >= 0) & (jj < lib.ny) & (ii >= 0) & (ii < lib.nx)
    k = (jj * lib.nx + ii)[ok]
    s = np.bincount(k, vel_fine[ok], minlength=lib.ny * lib.nx); n = np.bincount(k, minlength=lib.ny * lib.nx)
    media = np.where(n[lib.celle] >= 5, s[lib.celle] / np.maximum(n[lib.celle], 1), np.nan)
    r = media / np.where(sp_celle > 0.5, sp_celle, np.nan)
    G2 = np.where(np.isfinite(r) & (r > 0.05), G / np.where(np.isfinite(r) & (r > 0.05), r, 1.0), G)
    return np.clip(G2, 0.5, 2.0)


def livello(lib, G, vel_fine, mod_fine, mare_fine, lat_fine, lon_fine, scala_km=30.0):
    """0.58 (Giano, 26/11): il radar fissa solo il livello del vento oltre scala_km; sotto resta tutto il disegno di Lens,
    come la terza colonna. Fattore = exp(liscio(log g)) / liscio(Lens / modello), media gaussiana con sigma scala_km / 2
    sulla griglia della libreria, tra 0,5 e 2. Misurato sul radar in dieci aree: rispetto al primo Lens da solo gli
    errori migliorano o restano uguali dappertutto, e resta in mediana il 95% del disegno di Lens sopra il km (il
    relativo cella per cella ne lasciava il 12%). Come LensLivello del motore di Shift."""
    from scipy.ndimage import gaussian_filter, map_coordinates
    ny, nx = lib.ny, lib.nx
    LA, LO = np.meshgrid(lat_fine, lon_fine, indexing="ij")
    jf = (LA - lib.lat0) / lib.dlat; if_ = (LO - lib.lon0) / lib.dlon
    jj = np.rint(jf).astype(int); ii = np.rint(if_).astype(int)
    dentro = (jj >= 0) & (jj < ny) & (ii >= 0) & (ii < nx)
    ok = dentro & mare_fine & np.isfinite(vel_fine) & np.isfinite(mod_fine)
    k = (jj * nx + ii)[ok]; kt = (jj * nx + ii)[dentro]
    sl = np.bincount(k, vel_fine[ok], minlength=ny * nx); sm = np.bincount(k, mod_fine[ok], minlength=ny * nx)
    n = np.bincount(k, minlength=ny * nx); nt = np.bincount(kt, minlength=ny * nx)
    buono = (n >= 5) & (n >= 0.5 * np.maximum(nt, 1)) & (sm > 0.5 * np.maximum(n, 1))
    R = np.where(buono, sl / np.where(buono, sm, 1.0), 0.0).reshape(ny, nx); mR = buono.reshape(ny, nx).astype(float)
    lg = np.zeros(ny * nx); mg = np.zeros(ny * nx)
    okg = np.isfinite(G) & (G > 0)
    lg[lib.celle[okg]] = np.log(G[okg]); mg[lib.celle[okg]] = 1.0
    lg, mg = lg.reshape(ny, nx), mg.reshape(ny, nx)
    sig = scala_km / 2.0 / (lib.dlat * 111.19)
    lgS, mgS = gaussian_filter(lg, sig), gaussian_filter(mg, sig)
    rS, mRS = gaussian_filter(R, sig), gaussian_filter(mR, sig)
    gg = np.where(mgS > 1e-6, np.exp(lgS / np.maximum(mgS, 1e-6)), 1.0)
    rr = np.where(mRS > 1e-6, rS / np.maximum(mRS, 1e-6), 1.0)
    F = np.where(rr > 0.05, np.clip(gg / np.maximum(rr, 0.05), 0.5, 2.0), 1.0)
    return map_coordinates(F, [np.clip(jf, 0, ny - 1), np.clip(if_, 0, nx - 1)], order=1, mode="nearest")


def campo(lib, u_celle, v_celle, u925, v925, ora_utc, lat_fine, lon_fine, lens=None):
    """Fattore sulla griglia fine (ny, nx) per un'ora. u_celle, v_celle: vento del modello (m/s, verso est e nord) nei
    centri delle celle della libreria, letto dai punti di mare; u925, v925: vento medio a 925 hPa sull'area.
    lens: (forza di Lens sulla griglia fine, maschera del mare) per rendere il fattore relativo a Lens (0.57)."""
    sp = np.hypot(u_celle, v_celle)
    largo = lib.dist >= LARGO_KM
    if largo.sum() < 20:
        largo = lib.dist >= np.quantile(lib.dist[lib.dist > 0], 0.75)
    S0 = float(np.nanmedian(sp[largo]))
    D0 = np.radians(provenienza(np.nanmean(u_celle[largo]), np.nanmean(v_celle[largo])))
    s925 = float(np.hypot(u925, v925)); d925 = np.radians(provenienza(u925, v925))
    G = lib.fattore(S0 * np.sin(D0), S0 * np.cos(D0), s925 * np.sin(d925), s925 * np.cos(d925),
                    1.0 if ora_utc >= 12 else 0.0, provenienza(u_celle, v_celle))
    G = np.clip(np.nan_to_num(G, nan=1.0), 0.5, 2.0)
    info = {"S0": round(S0, 1), "G": [round(float(np.percentile(G, 5)), 2), round(float(np.median(G)), 2), round(float(np.percentile(G, 95)), 2)]}
    if lens is not None and len(lens) == 3:                    # 0.58: solo il livello a grande scala
        f = livello(lib, G, lens[0], lens[2], lens[1], lat_fine, lon_fine)
        info["livello"] = [round(float(np.min(f)), 2), round(float(np.max(f)), 2)]
        return f, info
    if lens is not None:
        G = relativo_a_lens(lib, G, sp, lens[0], lens[1], lat_fine, lon_fine)
    # sulla griglia fine: celle da 1 km piene (1 dove non c'e' cella), poi bilineare
    piena = np.ones(lib.ny * lib.nx, "f8"); piena[lib.celle] = G; piena = piena.reshape(lib.ny, lib.nx)
    from scipy.ndimage import map_coordinates
    LA, LO = np.meshgrid(lat_fine, lon_fine, indexing="ij")
    jj = (LA - lib.lat0) / lib.dlat; ii = (LO - lib.lon0) / lib.dlon
    f = map_coordinates(piena, [jj, ii], order=1, mode="constant", cval=1.0)
    return f, {"S0": round(S0, 1), "G": [round(float(np.percentile(G, 5)), 2), round(float(np.median(G)), 2), round(float(np.percentile(G, 95)), 2)]}

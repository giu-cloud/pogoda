"""Costruisce la pagina (HTML unico, senza risorse esterne) dalla previsione calcolata."""
import datetime as dt, html, json, math
from zoneinfo import ZoneInfo
from previsione.testi import TR, JS, GIORNI as GG, ROSA, NOMI_MODELLI
from comune.base import CFG

FUSO = ZoneInfo("Europe/Warsaw")
L = "pl"          # lingua in corso (la pagina viene composta una volta per lingua)
GIORNI = GG["pl"]


def lingua(l):
    global L, GIORNI
    L, GIORNI = l, GG[l]


def tr(k, **kw):
    v = TR[L][k]
    return v.format(**kw) if kw else v
PX, SX, DX, ORE_GRAF = 13, 34, 12, 72

CSS = """
:root{color-scheme:light dark;--bg:#f4f3ef;--card:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--ink3:#8a8984;--line:#e3e1da;
--c1:#2a78d6;--c2:#eb6834;--c5:#8a7fd6;--fog:#6f7f93;--ok:#1a7f4b;--warn:#b25e00;--bad:#c0392b;--chip:#eeece6}
@media (prefers-color-scheme:dark){:root{--bg:#121211;--card:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--ink3:#8d8c85;--line:#2e2e2b;
--c1:#3987e5;--c2:#d95926;--c5:#a197e8;--fog:#8fa0b5;--ok:#4cc38a;--warn:#e0a03a;--bad:#e66767;--chip:#262624}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:760px;margin:0 auto;padding:16px 14px 40px}
h1{font-size:1.5rem;margin:.2em 0 0}h2{font-size:1.05rem;margin:0 0 .6em}
.sub{color:var(--ink2);font-size:.9rem;margin:0 0 14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin:0 0 12px}
.ora{display:flex;gap:18px;align-items:baseline;flex-wrap:wrap}.big{font-size:3rem;font-weight:650;line-height:1}
.kv{color:var(--ink2);font-size:.92rem}.kv b{color:var(--ink);font-weight:600}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0;padding:0;list-style:none}
.chips li{background:var(--chip);border-radius:10px;padding:8px 10px;font-size:.92rem;border-left:4px solid var(--ink3)}
.chips li.w{border-left-color:var(--warn)}.chips li.b{border-left-color:var(--bad)}.chips li.g{border-left-color:var(--ok)}
table{border-collapse:collapse;width:100%;font-size:.9rem;font-variant-numeric:tabular-nums}
th,td{padding:6px 6px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th:first-child,td:first-child{text-align:left}th{color:var(--ink2);font-weight:600;font-size:.8rem}
.scorri{overflow-x:auto;-webkit-overflow-scrolling:touch}
.gt{position:sticky;left:0;display:inline-block;font-size:.85rem;font-weight:600;margin:10px 0 2px;background:var(--card);padding-right:8px}
.gt small{font-weight:400;color:var(--ink2)}
svg{display:block}svg text{font:11px system-ui,sans-serif;fill:var(--ink2)}
.gr{stroke:var(--line);stroke-width:1}.dy{stroke:var(--ink3);stroke-width:1;stroke-dasharray:2 3}
.l1{fill:none;stroke:var(--c1);stroke-width:2;stroke-linejoin:round}.l2{fill:none;stroke:var(--c2);stroke-width:2;stroke-linejoin:round}
.b1{fill:var(--c1);fill-opacity:.18}.f1{fill:var(--c1)}.f5{fill:var(--c5)}.ff{fill:var(--fog)}.wk{stroke:var(--ink3);stroke-width:1.5}
.zero{stroke:var(--ink);stroke-width:1;stroke-dasharray:4 3}
.leg{font-size:.8rem;color:var(--ink2);margin:2px 0 0}.leg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 4px 0 10px;vertical-align:-1px}
details summary{cursor:pointer;font-weight:600}.note{color:var(--ink2);font-size:.85rem}.note li{margin:.3em 0}
"""


def loc(t):
    return dt.datetime.fromisoformat(t).replace(tzinfo=dt.timezone.utc).astimezone(FUSO)


def e(x):
    return html.escape(str(x))


def f(x, n=0, u=""):
    if x is None:
        return "–"
    s = f"{x:.{n}f}".replace(".", ",").replace("-", "−")
    return s + u


def card_dir(g):
    if g is None:
        return ""
    return ROSA[L][int((g + 22.5) % 360 // 45)]


# ---------------- grafici ----------------
def cornice(ore, alto, ymin, ymax, passo, unita, corpo, zero=False):
    larg = SX + PX * len(ore) + DX
    y = lambda v: 8 + (alto - 26) * (1 - (v - ymin) / (ymax - ymin))
    s = [f'<svg width="{larg}" height="{alto}" viewBox="0 0 {larg} {alto}" role="img">']
    v = ymin
    while v <= ymax + 1e-9:
        s.append(f'<line class="gr" x1="{SX}" x2="{larg - DX}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>')
        s.append(f'<text x="{SX - 5}" y="{y(v) + 4:.1f}" text-anchor="end">{f(v)}</text>')
        v += passo
    for i, o in enumerate(ore):
        l = loc(o["t"])
        x = SX + i * PX
        if l.hour == 0:
            s.append(f'<line class="dy" x1="{x}" x2="{x}" y1="4" y2="{alto - 18}"/>')
            s.append(f'<text x="{x + 3}" y="{alto - 4}" font-weight="600">{GIORNI[l.weekday()]} {l.day}</text>')
        elif l.hour in (6, 12, 18):
            s.append(f'<text x="{x}" y="{alto - 4}" text-anchor="middle">{l.hour}</text>')
    if zero and ymin < 0 < ymax:
        s.append(f'<line class="zero" x1="{SX}" x2="{larg - DX}" y1="{y(0):.1f}" y2="{y(0):.1f}"/>')
    s.append(corpo(y))
    s.append(f'<text x="{SX + 4}" y="16">{unita}</text></svg>')
    return "".join(s)


def scala(vmin, vmax, minimo_span):
    import math
    span = max(vmax - vmin, minimo_span)
    passo = next(p for p in (1, 2, 5, 10, 20, 25, 50) if span / p <= 5)
    a = math.floor(vmin / passo) * passo
    b = math.ceil(vmax / passo) * passo
    if b - a < passo * 2:
        b = a + passo * 2
    return a, b, passo


def g_temp(ore):
    lo = [o["T10"] for o in ore if o["T10"] is not None]
    hi = [o["T90"] for o in ore if o["T90"] is not None]
    a, b, p = scala(min(lo), max(hi), 6)
    xc = lambda i: SX + i * PX + PX / 2

    def corpo(y):
        su = " ".join(f"{xc(i):.1f},{y(o['T90']):.1f}" for i, o in enumerate(ore))
        giu = " ".join(f"{xc(i):.1f},{y(o['T10']):.1f}" for i, o in reversed(list(enumerate(ore))))
        med = " ".join(f"{xc(i):.1f},{y(o['T']):.1f}" for i, o in enumerate(ore))
        return f'<polygon class="b1" points="{su} {giu}"/><polyline class="l1" points="{med}"/>'
    return cornice(ore, 170, a, b, p, "°C", corpo, zero=True)


def g_prec(ore):
    top = max([o["pr90"] or 0 for o in ore] + [o["pr"] or 0 for o in ore] + [1.0])
    a, b, p = scala(0, top, 2)

    def corpo(y):
        s = []
        for i, o in enumerate(ore):
            x = SX + i * PX + 1
            if o["pr"] and o["pr"] >= 0.1:
                h = y(0) - y(o["pr"])
                cl = "f5" if o["fase"] in ("neve", "mista") else "f1"
                s.append(f'<rect class="{cl}" x="{x}" y="{y(o["pr"]):.1f}" width="{PX - 2}" height="{h:.1f}" rx="2"><title>{loc(o["t"]):%d/%m %H}:00 · {f(o["pr"], 1)} mm</title></rect>')
            if o["pr90"] and o["pr90"] >= 0.3 and o["pr90"] > (o["pr"] or 0) + 0.1:
                s.append(f'<line class="wk" x1="{x + 2}" x2="{x + PX - 4}" y1="{y(o["pr90"]):.1f}" y2="{y(o["pr90"]):.1f}"/>')
        return "".join(s)
    return cornice(ore, 130, a, b, p, "mm/h", corpo)


def g_nube(ore):
    def corpo(y):
        s = []
        for i, o in enumerate(ore):
            v = (o["nube"] or 0) * 100
            if v > 0:
                s.append(f'<rect class="ff" x="{SX + i * PX + 1}" y="{y(v):.1f}" width="{PX - 2}" height="{y(0) - y(v):.1f}" rx="2" fill-opacity="{0.35 + 0.65 * v / 100:.2f}"><title>{loc(o["t"]):%d/%m %H}:00 · {v:.0f}%</title></rect>')
        return "".join(s)
    return cornice(ore, 110, 0, 100, 50, tr("u_n"), corpo)


def g_valle(ore):
    def corpo(y):
        s = []
        for i, o in enumerate(ore):
            v = (o["valle"] or 0) * 100
            if v > 0:
                s.append(f'<rect class="ff" x="{SX + i * PX + 1}" y="{y(v):.1f}" width="{PX - 2}" height="{y(0) - y(v):.1f}" rx="2" fill-opacity="{0.35 + 0.65 * v / 100:.2f}"><title>{loc(o["t"]):%d/%m %H}:00 · {v:.0f}%</title></rect>')
        return "".join(s)
    return cornice(ore, 96, 0, 100, 50, tr("u_n"), corpo)


def g_vento(ore):
    top = max([o["raffica"] or 0 for o in ore] + [o["vento"] or 0 for o in ore] + [20])
    a, b, p = scala(0, top, 20)
    xc = lambda i: SX + i * PX + PX / 2

    def corpo(y):
        r = " ".join(f"{xc(i):.1f},{y(o['raffica']):.1f}" for i, o in enumerate(ore) if o["raffica"] is not None)
        m = " ".join(f"{xc(i):.1f},{y(o['vento']):.1f}" for i, o in enumerate(ore) if o["vento"] is not None)
        return f'<polyline class="l2" points="{r}"/><polyline class="l1" points="{m}"/>'
    return cornice(ore, 130, a, b, p, "km/h", corpo)


# ---------------- testi ----------------
def quando(o):
    l = loc(o["t"])
    return tr("quando", g=GIORNI[l.weekday()], d=l.day, h=l.hour)


def avvisi(ore):
    o48 = ore[:48]
    out = []
    if not o48:
        return out
    gelo = [o for o in o48 if o["T"] is not None and o["T"] <= 0]
    tmin = min(o48, key=lambda o: o["T"])
    if gelo:
        out.append(("b", tr("gelo", q=quando(gelo[0]), t=f(tmin["T"], 1), q2=quando(tmin))))
    elif tmin["T10"] is not None and tmin["T10"] <= 0.5:
        out.append(("w", tr("gelata", t=f(tmin["T"], 1), t10=f(tmin["T10"], 1), q=quando(tmin))))
    else:
        out.append(("g", tr("no_gelo", t=f(tmin["T"], 1), q=quando(tmin))))
    neve = sum(o["neve_cm"] or 0 for o in o48)
    if neve >= 1:
        primo = next(o for o in o48 if (o["neve_cm"] or 0) > 0)
        out.append(("b" if neve >= 10 else "w", tr("neve", c=f(neve), q=quando(primo))))
    pioggia = sum((o["pr"] or 0) for o in o48 if o["fase"] == "pioggia")
    if pioggia >= 5:
        out.append(("w" if pioggia >= 20 else "", tr("pioggia", m=f(pioggia))))
    gel = [o for o in o48 if o["gelicidio"]]
    if gel:
        out.append(("b", tr("gelicidio", q=quando(gel[0]))))
    nb = [o for o in o48 if (o["nube"] or 0) >= 0.5]
    if nb:
        out.append(("w", tr("nube", n=len(nb), q=quando(nb[0]))))
    else:
        forse = [o for o in o48 if (o["nube"] or 0) >= 0.25]
        if forse:
            out.append(("", tr("nube_forse", n=len(forse))))
    vl = [o for o in o48 if (o["valle"] or 0) >= 0.4 and (o["nube"] or 0) < 0.4]
    if len(vl) >= 2:
        out.append(("", tr("valle", q=quando(vl[0]), n=len(vl))))
    gh = [o for o in o48 if o.get("ghiaccio")]
    if gh:
        out.append(("b" if len(gh) >= 6 else "w", tr("ghiaccio", n=len(gh), q=quando(gh[0]))))
    tp = [o for o in ore[:72] if (o.get("temporale") or 0) >= 0.25]
    if tp:
        forte = max(tp, key=lambda o: o["temporale"])
        out.append(("w", tr("temporale", q=quando(tp[0]), p=f(forte["temporale"] * 100))))
    rf = max(o48, key=lambda o: o["raffica"] or 0)
    if (rf["raffica"] or 0) >= 50:
        out.append(("b" if rf["raffica"] >= 75 else "w", tr("vento", r=f(rf["raffica"]), d=card_dir(rf["dir"]), q=quando(rf))))
    return out


def tabella(teste, righe):
    return "<table><tr>" + "".join(f"<th>{e(t)}</th>" for t in teste) + "</tr>" + "".join(righe) + "</table>"


def giorni(ore):
    per = {}
    for o in ore:
        per.setdefault(loc(o["t"]).date(), []).append(o)
    righe = []
    for d, v in list(per.items())[:6]:
        if len(v) < 6:
            continue
        t = [o["T"] for o in v if o["T"] is not None]
        righe.append(f"<tr><td>{GIORNI[d.weekday()]} {d.day}</td><td>{f(min(t))}° / {f(max(t))}°</td>"
                     f"<td>{f(sum((o['pr'] or 0) for o in v if o['fase'] != 'neve'))}</td><td>{f(sum(o['neve_cm'] or 0 for o in v))}</td>"
                     f"<td>{f(max((o['raffica'] or 0) for o in v))}</td><td>{sum(1 for o in v if (o['nube'] or 0) >= 0.5)}</td>"
                     f"<td>{min(o['n'] for o in v)}</td></tr>")
    return tabella(tr("g_h"), righe)


def orario(ore):
    r = []
    for o in ore[:48]:
        l = loc(o["t"])
        fen = tr("fen").get(o["fase"], "") if (o["pr"] or 0) >= 0.1 else ""
        r.append(f"<tr><td>{GIORNI[l.weekday()]} {l.hour:02d}</td><td>{f(o['T'], 1)}</td><td>{f(o['T10'])}…{f(o['T90'])}</td><td>{f(o['UR'])}</td>"
                 f"<td>{f(o['pr'], 1)} {fen}</td><td>{f(o['vento'])} / {f(o['raffica'])} {card_dir(o['dir'])}</td><td>{f((o['nube'] or 0) * 100)}%</td></tr>")
    return tabella(tr("o_h"), r)


def di_giorno(t):
    """Sole sopra l'orizzonte? Calcolo approssimato per la regione (49,5 N, 21 E), basta per scegliere l'icona."""
    n = t.timetuple().tm_yday
    decl = math.radians(-23.44 * math.cos(2 * math.pi * (n + 10) / 365))
    ang = math.radians(15 * (t.hour + t.minute / 60 + 21.0 / 15 - 12))
    fi = math.radians(49.5)
    return math.sin(fi) * math.sin(decl) + math.cos(fi) * math.cos(decl) * math.cos(ang) > 0


def icona(o):
    t = dt.datetime.fromisoformat(o["t"])
    if (o["pr"] or 0) >= 0.2:
        return "🌨️" if o["fase"] in ("neve", "mista") else "🌧️"
    if (o["nube"] or 0) >= 0.5:
        return "🌫️"
    g = di_giorno(t)
    n = o["nuv"] if o["nuv"] is not None else 50
    if n >= 80:
        return "☁️"
    if n >= 35:
        return "⛅" if g else "☁️"
    return "☀️" if g else "🌙"


def tessere(ore):
    out = []
    for k in (0, 3, 6, 12, 24, 36):
        if k >= len(ore):
            break
        o = ore[k]
        l = loc(o["t"])
        quando_ = tr("ora") if k == 0 else f"{GIORNI[l.weekday()]} {l.hour:02d}"
        gelo = ' style="color:var(--c1)"' if o["T"] is not None and o["T"] <= 0 else ""
        out.append(f'<div class="tes"><div class="tq">{quando_}</div><div class="ti">{icona(o)}</div><div class="tt"{gelo}>{f(o["T"])}°</div>'
                   f'<div class="tv">{f(o["raffica"])} km/h</div></div>')
    return '<div class="tessere">' + "".join(out) + "</div>"


def blocco_adesso(ris):
    a, ore, q = ris.get("adesso"), ris["ore"], ris["quota"]
    p = []
    o0 = ore[0] if ore else None
    if a and a.get("T_stima") is not None:
        p.append(f'<div class="ora"><div class="big">{f(a["T_stima"], 1)}°</div><div class="kv">{tr("stima")}<br>'
                 f'({e(", ".join(a["T_stima_da"][:5]))})</div></div>')
    elif o0:
        p.append(f'<div class="ora"><div class="big">{f(o0["T"], 1)}°</div><div class="kv">{tr("dai_modelli")}</div></div>')
    righe = []
    if o0:
        righe.append(tr("modelli_ora", t=f(o0["T"], 1), a=f(o0["T10"], 1), b=f(o0["T90"], 1), v=f(o0["vento"]), r=f(o0["raffica"]), d=card_dir(o0["dir"])))
    if a and a.get("base_nubi") is not None:
        b = a["base_nubi"]
        nome = e(a["base_da"]["nome"])
        righe.append(tr("base_sotto", b=f(b), st=nome) if b <= q + 25 else tr("base_sopra", b=f(b), d=f(b - q), st=nome))
    if a and a.get("nebbia_valle"):
        bd = a["base_da"]
        righe.append(tr("nebbia_valle", st=e(bd["nome"]), z=f(bd["quota"]), u=f(bd["UR"])))
    if a and a.get("grad_oss") is not None:
        st = tr("inv") if a.get("inversione") and a["grad_oss"] > 0 else (tr("stab") if a["grad_oss"] > -3 else tr("mix"))
        gd = a["grad_da"]
        righe.append(tr("grad", g=f(a["grad_oss"], 1), s=st, a=e(gd[0]), za=f(gd[1]), c=e(gd[2]), zc=f(gd[3])))
    p.append('<p class="kv">' + "<br>".join(righe) + "</p>")
    if a:
        t = [f"<tr><td>{e(s['nome'])}</td><td>{f(s['quota'])} m</td><td>{f(s['T'], 1)}°</td><td>{f(s['UR'])}%</td>"
             f"<td>{f(s['vento_kmh'])} {card_dir(s['dir'])}</td></tr>" for s in a["stazioni"]]
        ora = a["stazioni"][0].get("ora") or ""
        p.append(f"<details><summary>{tr('stazioni', h=e(ora[11:16]))}</summary>{tabella(tr('st_h'), t)}</details>")
    return "".join(p)


def corpo(ris, l, mappa):
    lingua(l)
    ore = ris["ore"]
    gen = dt.datetime.fromisoformat(ris["generato_utc"]).astimezone(FUSO)
    og = ore[:ORE_GRAF]
    av = "".join(f'<li class="{c}">{t}</li>' for c, t in avvisi(ore)) or f"<li>{tr('nessun')}</li>"
    letta = ris.get("previsioni_lette_utc")
    letta = dt.datetime.fromisoformat(letta).astimezone(FUSO).strftime("%d.%m %H:%M") if letta else "?"
    grafici = ""
    if len(og) >= 12:
        grafici = (f'<div class="card"><h2>{tr("grafici", n=len(og))}</h2><div class="scorri">'
                   f'<span class="gt">{tr("g_t")} <small>{tr("g_t2")}</small></span>{g_temp(og)}'
                   f'<span class="gt">{tr("g_p")} <small>{tr("g_p2")}</small></span>{g_prec(og)}'
                   f'<div class="leg"><i style="background:var(--c1)"></i>{tr("l_pioggia")}<i style="background:var(--c5)"></i>{tr("l_neve")}</div>'
                   f'<span class="gt">{tr("g_n")} <small>{tr("g_n2")}</small></span>{g_nube(og)}'
                   f'<span class="gt">{tr("g_f")} <small>{tr("g_f2")}</small></span>{g_valle(og)}'
                   f'<span class="gt">{tr("g_v")}</span>{g_vento(og)}'
                   f'<div class="leg"><i style="background:var(--c2)"></i>{tr("l_raff")}<i style="background:var(--c1)"></i>{tr("l_vento")}</div>'
                   f'</div></div>')
    mm = NOMI_MODELLI.get(next(iter(mappa.values()))["campi"].get("modello"), "–") if mappa else "–"
    note = "".join(f"<li>{n.format(mm=mm)}</li>" for n in tr("note")[: 5 if mappa else 4])
    segna = '<div class="card" data-mappa></div>' if mappa else ""
    return f"""<div class="lng" data-l="{l}">
<h1>{e(CFG['titolo'][l])} · {f(ris['quota'])} m</h1>
<p class="sub">{tr('sub', g=GIORNI[gen.weekday()], d=gen.strftime('%d.%m'), h=gen.strftime('%H:%M'), l=letta, n=len(ris['modelli']))}</p>
{tessere(ore)}
{segna}
<div class="card"><h2>{tr('adesso')}</h2>{blocco_adesso(ris)}</div>
<div class="card"><h2>{tr('h48')}</h2><ul class="chips">{av}</ul></div>
<div class="card"><h2>{tr('giorni')}</h2><div class="scorri">{giorni(ore)}</div></div>
{grafici}
<div class="card"><details><summary>{tr('orario')}</summary><div class="scorri">{orario(ore)}</div></details></div>
<div class="card"><h2>{tr('leggere')}</h2><ul class="note">{note}</ul><p class="note">{tr('fonti', m=e(', '.join(ris['modelli'])))}</p></div>
</div>"""


# ---------------- mappa ----------------
_QUI = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
CSS_MAPPA = open(__import__("os").path.join(_QUI, "mappa.css"), encoding="utf-8").read()
JS_MAPPA = open(__import__("os").path.join(_QUI, "mappa.js"), encoding="utf-8").read()


def svg_mappa(ris, mappa, lato):
    """Etichette sopra la carta: stazioni vere con la temperatura, paesi, cime, e la casa al centro."""
    p = []
    presi = [(0.40, 0.46, 0.60, 0.515)]  # riquadri gia' occupati: la casa e la sua scritta
    fiumi = []
    for i, fl in enumerate(mappa["base"].get("nomi_fiumi", [])):
        d = "M" + " L".join(f"{x * 1000:.0f} {y * 1000:.0f}" for x, y in fl["p"])
        fiumi.append(f'<path id="f{lato}_{i}" d="{d}" fill="none"/><text class="fi" dy="-7"><textPath href="#f{lato}_{i}" startOffset="50%" text-anchor="middle">{e(fl["n"])}</textPath></text>')
    def posto(x, y, testo, largo):
        """Riquadro della scritta, a destra del punto o a sinistra se non ci sta. None se si sovrappone."""
        w = len(testo) * largo + 0.03
        for verso in (1, -1):
            x0, x1 = (x - 0.012, x + w) if verso > 0 else (x - w, x + 0.012)
            r = (x0, y - 0.024, x1, y + 0.024)
            if x0 > 0.005 and x1 < 0.995 and 0.03 < y < 0.975 and all(r[2] < q[0] or r[0] > q[2] or r[3] < q[1] or r[1] > q[3] for q in presi):
                presi.append(r)
                return verso
        return None
    for s in sorted(ris.get("mappa_stazioni", {}).get(lato, []), key=lambda s: s.get("T") is None):
        x, y = s["x"], s["y"]
        if s.get("T") is not None:
            testo = f'{s["n"]} {f(s["T"], 1)}°'
            v = posto(x, y, testo, 0.0128)
            if v:
                p.append(f'<circle cx="{x * 1000:.0f}" cy="{y * 1000:.0f}" r="8" fill="#fffdf5" stroke="#14140f" stroke-width="3"/>'
                         f'<text class="st" x="{x * 1000 + 14 * v:.0f}" y="{y * 1000 + 8:.0f}" text-anchor="{"start" if v > 0 else "end"}">{e(testo)}</text>')
        else:
            v = posto(x, y, s["n"], 0.0108)
            if v:
                p.append(f'<circle cx="{x * 1000:.0f}" cy="{y * 1000:.0f}" r="4" fill="#33332c"/>'
                         f'<text class="pi" x="{x * 1000 + 12 * v:.0f}" y="{y * 1000 + 7:.0f}" text-anchor="{"start" if v > 0 else "end"}">{e(s["n"])}</text>')
    for c in mappa["base"].get("paesi", []):
        cl = {1: "pi mi", 0: "pi", -1: "pi fr"}.get(c.get("c", 0), "pi")
        v = posto(c["x"], c["y"], c["n"], 0.017 if c.get("c") == 1 else 0.013)
        if v:
            p.append(f'<circle cx="{c["x"] * 1000:.0f}" cy="{c["y"] * 1000:.0f}" r="{5 if c.get("c") == 1 else 4}" fill="none" stroke="#2a2118" stroke-width="2.5"/>'
                     f'<text class="{cl}" x="{c["x"] * 1000 + 12 * v:.0f}" y="{c["y"] * 1000 + 8:.0f}" text-anchor="{"start" if v > 0 else "end"}">{e(c["n"])}</text>')
    for c in mappa["base"].get("cime", []):
        testo = f'{c["n"]} {c["q"]}'
        v = posto(c["x"], c["y"], testo, 0.0108)
        if v:
            p.append(f'<path d="M{c["x"] * 1000 - 9:.0f} {c["y"] * 1000 + 7:.0f}l9 -15l9 15z" fill="#5a3d1e"/>'
                     f'<text class="ci" x="{c["x"] * 1000 + 14 * v:.0f}" y="{c["y"] * 1000 + 7:.0f}" text-anchor="{"start" if v > 0 else "end"}">{e(testo)}</text>')
    casa = ('<g transform="translate(500 500)"><circle r="9" fill="#c0392b" stroke="#fffdf5" stroke-width="4"/>'
            '<text class="casa-t" x="0" y="-20" text-anchor="middle"></text></g>')
    return (f'<svg data-k="{lato}" viewBox="0 0 1000 1000" preserveAspectRatio="none">{"".join(fiumi)}{"".join(p)}{casa}'
            '<g class="sg" visibility="hidden"><circle r="13" fill="none" stroke="#fffdf5" stroke-width="6"/><circle r="13" fill="none" stroke="#14140f" stroke-width="2.5"/></g></svg>')


def blocco_mappa(ris, mappe):
    chiavi = sorted(mappe, key=lambda k: -int(k))
    primo = mappe[chiavi[0]]["campi"]
    suolo = next((o.get("suolo_cm") for o in ris["ore"][:3] if o.get("suolo_cm") is not None), None)
    dati = {"casa": CFG["casa"], "quota": round(ris["quota"]), "suolo": suolo, "modello": NOMI_MODELLI.get(primo.get("modello"), primo.get("modello")), "k": chiavi,
            "m": {k: {"n": m["base"]["n"], "dem": m["base"]["dem"], "c": m["campi"], "v": m.get("vento")} for k, m in mappe.items()}}
    scale = "".join(f'<button type="button" data-k="{k}">{k} × {k} km</button>' for k in chiavi)
    strati_img = "".join(f'<img data-k="{k}" alt="" src="data:image/jpeg;base64,{mappe[k]["jpg"]}">' for k in chiavi)
    etichette = "".join(svg_mappa(ris, mappe[k], k) for k in chiavi)
    nascosto = ' hidden' if len(chiavi) < 2 else ''
    nord = ('<svg class="nord" viewBox="0 0 26 34"><path d="M13 2L20 22L13 18L6 22Z" fill="#222" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/>'
            '<text x="13" y="32" text-anchor="middle" style="font:700 10px system-ui;fill:#222;stroke:#fff;stroke-width:3px;paint-order:stroke">N</text></svg>')
    html_ = (f'<div id="mappa"><div class="strati" id="scale"{nascosto}>{scale}</div><div class="strati" id="strati"></div><div class="strati" id="strati2" hidden></div>'
             f'<div class="mw" id="mw">{strati_img}<canvas id="ov" width="150" height="150"></canvas><canvas id="lc"></canvas><canvas id="pc"></canvas>{etichette}'
             f'{nord}<div class="sb" id="sb"></div><div id="mk"></div><button type="button" id="flx" aria-pressed="false">≋</button></div>'
             '<div class="tempo"><button type="button" class="tb" id="pr" aria-label="-1 h">‹</button><button type="button" class="tb" id="play" aria-label="play">▶</button>'
             '<button type="button" class="tb" id="nx" aria-label="+1 h">›</button><div class="cursore"><input type="range" id="cur" min="0" max="47" value="0" aria-label="czas"><div id="gg"></div></div></div>'
             '<div class="tl" id="tl"></div><div class="leg" id="leg"></div><div class="info" id="info"></div></div>')
    js = JS_MAPPA.replace("__DATI__", json.dumps(dati, separators=(",", ":"))).replace("__TXT__", json.dumps(JS, ensure_ascii=False))
    return html_, js


def fonti():
    """EB Garamond (SIL Open Font License) incorporato: le scritte della carta non dipendono dalla rete."""
    import base64, os
    cart = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonti")
    gamme = {"latin": "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2212",
             "latin-ext": "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+1E00-1E9F,U+2C60-2C7F,U+A720-A7FF"}
    out = ""
    for sub, gamma in gamme.items():
        for stile in ("normal", "italic"):
            f = os.path.join(cart, f"eb-garamond-{sub}-500-{stile}.woff2")
            if os.path.exists(f):
                b = base64.b64encode(open(f, "rb").read()).decode()
                out += (f"@font-face{{font-family:'Garamond Stara';font-style:{stile};font-weight:500;font-display:swap;"
                        f"src:url(data:font/woff2;base64,{b}) format('woff2');unicode-range:{gamma}}}")
    return out


def pagina(ris, mappa=None):
    mappa = {k: m for k, m in (mappa or {}).items() if m.get("base") and m.get("campi") and m.get("jpg")} or None
    corpi = "".join(corpo(ris, l, mappa) for l in ("pl", "it"))
    if mappa:
        mh, js = blocco_mappa(ris, mappa)
    else:
        mh, js = "", JS_MAPPA.replace("__DATI__", "null").replace("__TXT__", json.dumps(JS, ensure_ascii=False))
    return f"""<!DOCTYPE html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>{e(CFG['titolo']['pl'])}</title><style>{fonti() if mappa else ''}{CSS}{CSS_MAPPA}</style></head><body data-l="pl"><main>
<div class="lsw"><button type="button" data-l="pl" aria-pressed="true">PL</button><button type="button" data-l="it" aria-pressed="false">IT</button></div>
{corpi}
<div hidden>{mh}</div>
</main><script>{js}</script></body></html>"""

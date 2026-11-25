"""Prepara il sito pubblicato su GitHub Pages: una cartella per casa, con la pagina,
il manifest e le icone per aggiungerla alla schermata Home come un'app."""
import json, os, shutil

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.join(QUI, "..")
SITO = os.path.join(RADICE, "_site")

CASE = [  # cartella del sito, suffisso dei dati, nome sotto l'icona, colore della barra
    ("nowica", "", "Nowica", "#46789f"),
    ("fiodor", "_b", "Fiodor's place", "#785fa0"),
]

TESTA = """<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/png" sizes="192x192" href="icona_192.png">
<link rel="apple-touch-icon" href="icona_180.png">
<meta name="theme-color" content="{colore}">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="{nome}">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
"""

# Avviso se i dati sono vecchi (il giro e' ogni 3 ore, con ritardi fino a un'ora),
# e ricarica la pagina quando la si riapre dall'icona dopo un po'.
CODA = """<div id="vecchio" style="display:none;position:fixed;left:8px;right:8px;bottom:8px;z-index:99;
background:#fff3cd;color:#5c4400;border:1px solid #e6c65c;border-radius:10px;padding:10px 12px;
font:14px/1.35 system-ui,sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.15)"></div>
<script>
(function(){
  var gen = new Date("__GEN__"), aperta = Date.now();
  function controlla(){
    var ore = (Date.now() - gen.getTime()) / 3600000, b = document.getElementById("vecchio");
    if (ore > 8) {
      var pl = document.body.getAttribute("data-l") !== "it";
      var h = Math.floor(ore);
      b.textContent = pl ? ("Prognoza nie była aktualizowana od " + h + " godz. Dane mogą być nieaktualne.")
                         : ("La previsione non si aggiorna da " + h + " ore. I dati potrebbero essere vecchi.");
      b.style.display = "block";
    } else { b.style.display = "none"; }
  }
  controlla();
  document.addEventListener("visibilitychange", function(){
    if (document.visibilityState !== "visible") return;
    if (Date.now() - aperta > 30 * 60000) { location.reload(); } else { controlla(); }
  });
})();
</script>
"""


def main():
    if os.path.isdir(SITO):
        shutil.rmtree(SITO)
    os.makedirs(SITO)
    fatte = 0
    for cartella, suf, nome, colore in CASE:
        usc = os.path.join(RADICE, "previsione", "uscita" + suf)
        pag = os.path.join(usc, "pagina.html")
        if not os.path.exists(pag):
            print(f"{cartella}: pagina mancante, salto")
            continue
        gen = json.load(open(os.path.join(usc, "previsione.json"), encoding="utf-8"))["generato_utc"]
        html = open(pag, encoding="utf-8").read()
        html = html.replace("</head>", TESTA.format(nome=nome, colore=colore) + "</head>", 1)
        html = html.replace("</body>", CODA.replace("__GEN__", gen) + "</body>", 1)
        dest = os.path.join(SITO, cartella)
        os.makedirs(dest)
        open(os.path.join(dest, "index.html"), "w", encoding="utf-8").write(html)
        for f in os.listdir(os.path.join(QUI, cartella)):
            shutil.copy(os.path.join(QUI, cartella, f), dest)
        man = {"name": nome, "short_name": nome, "start_url": "./", "scope": "./", "display": "standalone",
               "background_color": "#ffffff", "theme_color": colore,
               "icons": [{"src": "icona_192.png", "sizes": "192x192", "type": "image/png"},
                         {"src": "icona_512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]}
        json.dump(man, open(os.path.join(dest, "manifest.webmanifest"), "w", encoding="utf-8"), ensure_ascii=False)
        print(f"{cartella}: pagina del {gen}")
        fatte += 1
    open(os.path.join(SITO, "index.html"), "w", encoding="utf-8").write(
        '<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex,nofollow"><title>pogoda</title>')
    # Pietro: la pagina la calcola il lavoro "pietro" e la lascia nella release "pietro"; qui si prende l'ultima
    try:
        import urllib.request
        dest = os.path.join(SITO, "pietro")
        os.makedirs(dest, exist_ok=True)
        req = urllib.request.Request("https://github.com/giu-cloud/pogoda/releases/download/pietro/pietro.html",
                                     headers={"User-Agent": "pogoda"})
        open(os.path.join(dest, "index.html"), "wb").write(urllib.request.urlopen(req, timeout=60).read())
        for f in os.listdir(os.path.join(QUI, "pietro")):
            shutil.copy(os.path.join(QUI, "pietro", f), dest)
        json.dump({"name": "Pietro", "short_name": "Pietro", "start_url": "./", "scope": "./", "display": "standalone",
                   "background_color": "#f2f1ec", "theme_color": "#1f5fa8",
                   "icons": [{"src": "icona_192.png", "sizes": "192x192", "type": "image/png"},
                             {"src": "icona_512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]},
                  open(os.path.join(dest, "manifest.webmanifest"), "w"))
        print("pietro: pagina presa dalla release")
    except Exception as e:
        print("pietro: pagina non disponibile:", e)
        shutil.rmtree(os.path.join(SITO, "pietro"), ignore_errors=True)
    # il primo indirizzo della seconda casa porta a quello nuovo
    os.makedirs(os.path.join(SITO, "feodor"), exist_ok=True)
    open(os.path.join(SITO, "feodor", "index.html"), "w", encoding="utf-8").write(
        '<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=../fiodor/"><link rel="canonical" href="../fiodor/">')
    open(os.path.join(SITO, "robots.txt"), "w").write("User-agent: *\nDisallow: /\n")
    if not fatte:
        raise SystemExit("nessuna pagina da pubblicare")


if __name__ == "__main__":
    main()

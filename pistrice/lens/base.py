"""Richieste web di Lens: ritornano lo stato e il contenuto, senza sollevare eccezioni."""
import json, time, urllib.request, urllib.error

UA = {"User-Agent": "shift-lens/0.1 (progetto personale non commerciale)"}


def scarica(url, timeout=40, tentativi=2, grezzo=False):
    """Ritorna (stato, contenuto). L'errore torna come testo."""
    ultimo = "?"
    for i in range(tentativi):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                dati = r.read()
                return r.status, (dati if grezzo else dati.decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            corpo = e.read()[:400].decode("utf-8", "replace")
            ultimo = f"HTTP {e.code}: {corpo}"
            if e.code in (400, 403, 404):
                return e.code, ultimo
        except Exception as e:  # rete, timeout
            ultimo = f"{type(e).__name__}: {e}"
        time.sleep(3 * (i + 1))
    return 0, ultimo


def scarica_json(url, **kw):
    stato, testo = scarica(url, **kw)
    if stato != 200:
        return stato, testo
    try:
        return 200, json.loads(testo)
    except Exception as e:
        return 0, f"JSON non valido: {e}"

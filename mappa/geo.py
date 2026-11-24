"""Geometria delle mappe: quadrati centrati sulla casa, uno largo e uno ravvicinato.
Il riquadro si ricalcola ogni volta dai Secrets e non si scrive mai nei file."""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from comune.base import CFG

LATI = CFG["lati"]  # km di lato delle mappe di questa casa
G = 13  # punti per lato della griglia dei campi meteo


def riquadro(lat, lon, lato):
    dlat = (lato / 2) / 111.19
    dlon = (lato / 2) / (111.19 * math.cos(math.radians(lat)))
    return lat - dlat, lat + dlat, lon - dlon, lon + dlon  # S, N, O, E


def griglia(lat, lon, lato):
    s, n, o, e = riquadro(lat, lon, lato)
    return [(n - r * (n - s) / (G - 1), o + c * (e - o) / (G - 1)) for r in range(G) for c in range(G)]  # riga 0 = nord

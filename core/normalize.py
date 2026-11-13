"""Normalización de texto y de precios entre mercados.

Cada mercado expone los precios distinto:
  * VTEX (Carrefour, Vea, Día) y Monarca -> número JSON (float)
  * Golopolis -> string con formato US: "6,354.42" (coma = miles, punto = decimal)
"""
import unicodedata
from typing import List


def norm(text: str) -> str:
    """Minúsculas, sin acentos y sin espacios sobrantes."""
    t = unicodedata.normalize("NFKD", text or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.lower().split())


def tokens(query: str) -> List[str]:
    """Palabras significativas del query (>= 3 letras), o todas si ninguna califica."""
    toks = [t for t in norm(query).split() if len(t) >= 3]
    return toks or norm(query).split()


def money(value: float) -> str:
    """Formato argentino: 1234.5 -> $1.234,50"""
    return "$" + f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_us_price(text: str) -> float:
    """Convierte '6,354.42' (formato US) a 6354.42. Devuelve 0.0 si no se puede."""
    limpio = (text or "").replace("$", "").replace(" ", "")
    limpio = limpio.replace(",", "")
    try:
        return float(limpio)
    except ValueError:
        return 0.0

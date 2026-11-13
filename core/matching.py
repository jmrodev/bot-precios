"""Comparación: filtrado por relevancia y agrupado del mismo producto entre mercados."""
from typing import Dict, Iterable, List

from .models import Offer, ProductGroup
from .normalize import norm, tokens


def _score(name: str, toks: List[str]) -> int:
    n = norm(name)
    return sum(1 for t in toks if t in n)


def filter_relevant(offers: Iterable[Offer], query: str) -> List[Offer]:
    """Descarta resultados que no contienen las palabras buscadas.

    Primero exige TODAS las palabras; si eso deja la lista vacía, acepta al menos una.
    Si tampoco, devuelve lo que vino (mejor mostrar algo que nada).
    """
    offers = list(offers)
    if not offers:
        return []
    toks = tokens(query)
    estrictos = [o for o in offers if _score(o.product, toks) == len(toks)]
    if estrictos:
        return estrictos
    relajados = [o for o in offers if _score(o.product, toks) >= 1]
    return relajados or offers


def group_products(offers: Iterable[Offer]) -> List[ProductGroup]:
    """Agrupa ofertas del mismo producto: por EAN si lo hay, si no por nombre normalizado.

    Dentro de cada grupo deja una sola oferta por mercado (la más barata) y ordena por precio.
    Orden de salida: primero los productos comparables en más mercados, después por precio.
    """
    grupos: Dict[str, Dict] = {}

    for o in offers:
        ean = (o.ean or "").strip()
        key = f"ean:{ean}" if len(ean) >= 8 else f"name:{norm(o.product)[:40]}"
        grupo = grupos.setdefault(key, {"title": o.product, "offers": {}})

        if len(o.product) > len(grupo["title"]):
            grupo["title"] = o.product

        previa = grupo["offers"].get(o.market)
        if previa is None or o.price < previa.price:
            grupo["offers"][o.market] = o

    salida = [
        ProductGroup(
            title=g["title"],
            offers=tuple(sorted(g["offers"].values(), key=lambda x: x.price)),
        )
        for g in grupos.values()
    ]
    salida.sort(key=lambda g: (-len(g.offers), g.offers[0].price))
    return salida

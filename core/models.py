"""Modelos del dominio. Todos los providers devuelven el mismo tipo: Offer."""
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Offer:
    """Una oferta comprable de un mercado para un producto.

    Los providers no devuelven productos sin stock: un precio que no se puede
    pagar no es una oferta.
    """
    market: str
    product: str
    brand: str = ""
    ean: str = ""
    price: float = 0.0
    list_price: float = 0.0
    link: str = ""


@dataclass(frozen=True)
class ProductGroup:
    """El mismo producto (por EAN o nombre) ofrecido en uno o más mercados."""
    title: str
    offers: Tuple[Offer, ...]

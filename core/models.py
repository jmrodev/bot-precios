"""Modelos del dominio. Todos los providers devuelven el mismo tipo: Offer."""
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Offer:
    """Una oferta concreta de un mercado para un producto."""
    market: str
    product: str
    brand: str = ""
    ean: str = ""
    price: float = 0.0
    list_price: float = 0.0
    available: bool = True
    link: str = ""


@dataclass(frozen=True)
class ProductGroup:
    """El mismo producto (por EAN o nombre) ofrecido en uno o más mercados."""
    title: str
    offers: Tuple[Offer, ...]

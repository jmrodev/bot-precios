"""Dominio de ComparaPrecios AR: providers, normalización y comparación.

Regla de arquitectura: `core` no sabe de Telegram, ni de HTTP, ni de FastAPI.
Es Python puro (más aiohttp para los fetch) y se testea sin red con `fixtures/`.
"""
from .models import Offer, ProductGroup
from .normalize import norm, tokens, money, parse_us_price
from .matching import filter_relevant, group_products
from .providers import PROVIDERS, MARKETS, search_all

__all__ = [
    "Offer",
    "ProductGroup",
    "norm",
    "tokens",
    "money",
    "parse_us_price",
    "filter_relevant",
    "group_products",
    "PROVIDERS",
    "MARKETS",
    "search_all",
]

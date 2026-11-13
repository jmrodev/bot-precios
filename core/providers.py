"""Providers: una clase por mercado, todas devuelven list[Offer].

Cada provider separa `fetch` (red, async) de `parse` (puro), y `parse` es lo que
testean los tests usando `fixtures/` — sin tocar la red.
"""
import html as html_lib
import re
import urllib.parse
from typing import Any, Dict, List

import aiohttp

from .models import Offer
from .normalize import parse_us_price

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
TIMEOUT = aiohttp.ClientTimeout(total=10)


class VtexProvider:
    """Carrefour, Vea, Día: API pública de catálogo VTEX."""

    def __init__(self, market: str, domain: str):
        self.market = market
        self.domain = domain

    def url(self, query: str, limit: int) -> str:
        q = urllib.parse.quote(query)
        return f"https://{self.domain}/api/catalog_system/pub/products/search?ft={q}&_from=0&_to={limit - 1}"

    def parse(self, payload: Any, limit: int = 6) -> List[Offer]:
        ofertas = []
        for item in payload or []:
            items = item.get("items") or []
            if not items:
                continue
            sku = items[0]
            sellers = sku.get("sellers") or []
            if not sellers:
                continue
            oferta = sellers[0].get("commertialOffer") or {}
            price = float(oferta.get("Price") or 0)
            if price <= 0:
                continue
            ofertas.append(Offer(
                market=self.market,
                product=(item.get("productName") or "").strip(),
                brand=(item.get("brand") or "").strip(),
                ean=str(sku.get("ean") or ""),
                price=price,
                list_price=float(oferta.get("ListPrice") or 0),
                available=int(oferta.get("AvailableQuantity") or 0) > 0,
                link=item.get("link") or "",
            ))
            if len(ofertas) >= limit:
                break
        return ofertas

    async def fetch(self, session: aiohttp.ClientSession, query: str, limit: int) -> List[Offer]:
        async with session.get(self.url(query, limit), headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, timeout=TIMEOUT) as resp:
            if resp.status not in (200, 206):
                return []
            return self.parse(await resp.json(content_type=None), limit)


class MonarcaProvider:
    """Monarca (Tandil): API JSON propia de su tienda Next.js."""

    market = "Monarca"
    base = "https://api.monarcadigital.com.ar"

    def url(self, query: str, limit: int) -> str:
        return f"{self.base}/products/search?page=0&query={urllib.parse.quote(query)}&size={limit}"

    def parse(self, payload: Any, limit: int = 6) -> List[Offer]:
        ofertas = []
        productos = ((payload or {}).get("products") or {}).get("content") or []
        for item in productos:
            price = float(item.get("price") or 0)
            if price <= 0:
                continue
            nombre = (item.get("description") or "").strip()
            presentacion = (item.get("presentation") or "").strip()
            if presentacion:
                nombre = f"{nombre} {presentacion}"
            ofertas.append(Offer(
                market=self.market,
                product=nombre,
                brand=(item.get("brand") or "").strip(),
                ean=str(item.get("barcode") or ""),
                price=price,
                list_price=price,
                available=item.get("status") == "Publicado",
                link="",
            ))
        return ofertas[:limit]

    async def fetch(self, session: aiohttp.ClientSession, query: str, limit: int) -> List[Offer]:
        async with session.get(self.url(query, limit), headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, timeout=TIMEOUT) as resp:
            if resp.status != 200:
                return []
            return self.parse(await resp.json(content_type=None), limit)


class GolopolisProvider:
    """Golopolis (Tandil): catálogo HTML server-rendered."""

    market = "Golopolis"
    base = "https://www.golopolis.com.ar/app/?action=products&search="
    CARD = '<div class="col-6 col-md-4'
    ITEM = re.compile(r'action=detail&itemId=(\d+)"[^>]*>([^<]{2,120})</a></h2>')
    PRICE = re.compile(r'class="new-price">\s*\$?([\d.,]+)')
    EAN = re.compile(r"/products/\d+_(\d{8,14})\.(?:jpg|jpeg|png|webp)")

    def url(self, query: str, limit: int) -> str:
        return self.base + urllib.parse.quote(query)

    def parse(self, payload: str, limit: int = 6) -> List[Offer]:
        ofertas = []
        for bloque in (payload or "").split(self.CARD)[1:]:
            if len(ofertas) >= limit:
                break
            item = self.ITEM.search(bloque)
            precio = self.PRICE.search(bloque)
            if not item or not precio:
                continue
            price = parse_us_price(precio.group(1))
            if price <= 0:
                continue
            ean = self.EAN.search(bloque)
            ofertas.append(Offer(
                market=self.market,
                product=html_lib.unescape(item.group(2)).strip(),
                ean=ean.group(1) if ean else "",
                price=price,
                list_price=price,
                available=True,
                link=f"https://www.golopolis.com.ar/app/?action=detail&itemId={item.group(1)}",
            ))
        return ofertas

    async def fetch(self, session: aiohttp.ClientSession, query: str, limit: int) -> List[Offer]:
        headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
        async with session.get(self.url(query, limit), headers=headers, timeout=TIMEOUT) as resp:
            if resp.status != 200:
                return []
            return self.parse(await resp.text(errors="ignore"), limit)


PROVIDERS = [
    VtexProvider("Carrefour", "www.carrefour.com.ar"),
    VtexProvider("Vea", "www.vea.com.ar"),
    VtexProvider("Día", "diaonline.supermercadosdia.com.ar"),
    MonarcaProvider(),
    GolopolisProvider(),
]

MARKETS = [p.market for p in PROVIDERS]


async def _fetch_safe(provider, session, query: str, limit: int) -> List[Offer]:
    try:
        return await provider.fetch(session, query, limit)
    except Exception as e:  # un mercado caído no debe romper la búsqueda
        print(f"Error fetching {provider.market}: {e}")
        return []


async def search_all(query: str, limit: int = 6) -> List[Offer]:
    """Consulta todos los providers en paralelo y devuelve las ofertas ordenadas por precio."""
    import asyncio

    async with aiohttp.ClientSession() as session:
        resultados = await asyncio.gather(
            *(_fetch_safe(p, session, query, limit) for p in PROVIDERS)
        )
    ofertas = [o for r in resultados for o in r]
    ofertas.sort(key=lambda o: o.price)
    return ofertas

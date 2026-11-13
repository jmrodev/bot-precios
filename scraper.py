import asyncio
import aiohttp
import html
import re
from typing import List, Dict, Any
import urllib.parse

# Cadenas con sucursal en Tandil que exponen la API VTEX de catálogo.
VTEX_STORES = [
    ("Carrefour", "www.carrefour.com.ar"),
    ("Vea", "www.vea.com.ar"),
    ("Día", "diaonline.supermercadosdia.com.ar"),
]

MONARCA_API = "https://api.monarcadigital.com.ar"

# Golopolis (Tandil) sirve el catálogo como HTML server-rendered.
GOLOPOLIS_URL = "https://www.golopolis.com.ar/app/?action=products&search={query}"
GOLOPOLIS_CARDS = '<div class="col-6 col-md-4'
GOLOPOLIS_ITEM = re.compile(r'action=detail&itemId=(\d+)"[^>]*>([^<]{2,120})</a></h2>')
GOLOPOLIS_PRICE = re.compile(r'class="new-price">\s*\$?([\d.,]+)')
GOLOPOLIS_EAN = re.compile(r'/products/\d+_(\d{8,14})\.(?:jpg|jpeg|png|webp)')

# Orden en que se muestran en los mensajes del bot.
MARKETS = [name for name, _ in VTEX_STORES] + ["Monarca", "Golopolis"]


class RetailScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Accept": "application/json",
        }

    async def _fetch_vtex(self, session: aiohttp.ClientSession, store_name: str, domain: str, query: str, limit: int = 4) -> List[Dict[str, Any]]:
        q = urllib.parse.quote(query)
        url = f"https://{domain}/api/catalog_system/pub/products/search?ft={q}&_from=0&_to={limit - 1}"
        results = []
        try:
            async with session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=8)) as response:
                if response.status in (200, 206):
                    data = await response.json(content_type=None)
                    for item in data:
                        name = item.get("productName", "").strip()
                        brand = item.get("brand", "").strip()
                        sku_items = item.get("items", [])
                        if not sku_items:
                            continue
                        sku = sku_items[0]
                        ean = sku.get("ean", "")
                        sellers = sku.get("sellers", [])
                        if not sellers:
                            continue
                        comm = sellers[0].get("commertialOffer", {})
                        price = comm.get("Price", 0.0)
                        list_price = comm.get("ListPrice", 0.0)
                        available = comm.get("AvailableQuantity", 0) > 0
                        link = item.get("link", "")

                        if price > 0:
                            results.append({
                                "supermercado": store_name,
                                "producto": name,
                                "marca": brand,
                                "ean": ean,
                                "precio": price,
                                "precio_lista": list_price,
                                "disponible": available,
                                "link": link
                            })
        except Exception as e:
            print(f"Error fetching {store_name}: {e}")
        return results

    async def _fetch_monarca(self, session: aiohttp.ClientSession, query: str, limit: int = 4) -> List[Dict[str, Any]]:
        q = urllib.parse.quote(query)
        url = f"{MONARCA_API}/products/search?page=0&query={q}&size={limit}"
        results = []
        try:
            async with session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=8)) as response:
                if response.status == 200:
                    data = await response.json(content_type=None)
                    for item in data.get("products", {}).get("content", []):
                        price = float(item.get("price") or 0)
                        if price <= 0:
                            continue
                        name = (item.get("description") or "").strip()
                        presentation = (item.get("presentation") or "").strip()
                        if presentation:
                            name = f"{name} {presentation}"
                        results.append({
                            "supermercado": "Monarca",
                            "producto": name,
                            "marca": (item.get("brand") or "").strip(),
                            "ean": item.get("barcode") or "",
                            "precio": price,
                            "precio_lista": price,
                            "disponible": item.get("status") == "Publicado",
                            "link": ""
                        })
        except Exception as e:
            print(f"Error fetching Monarca: {e}")
        return results

    async def _fetch_golopolis(self, session: aiohttp.ClientSession, query: str, limit: int = 4) -> List[Dict[str, Any]]:
        url = GOLOPOLIS_URL.format(query=urllib.parse.quote(query))
        results = []
        headers = dict(self.headers)
        headers["Accept"] = "text/html,application/xhtml+xml"
        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    text = await response.text(errors="ignore")
                    for block in text.split(GOLOPOLIS_CARDS)[1:]:
                        if len(results) >= limit:
                            break
                        item = GOLOPOLIS_ITEM.search(block)
                        price_match = GOLOPOLIS_PRICE.search(block)
                        if not item or not price_match:
                            continue
                        try:
                            # Golopolis usa formato US: coma = miles, punto = decimal
                            price = float(price_match.group(1).replace(",", ""))
                        except ValueError:
                            continue
                        if price <= 0:
                            continue
                        ean_match = GOLOPOLIS_EAN.search(block)
                        product_id = item.group(1)
                        results.append({
                            "supermercado": "Golopolis",
                            "producto": html.unescape(item.group(2)).strip(),
                            "marca": "",
                            "ean": ean_match.group(1) if ean_match else "",
                            "precio": price,
                            "precio_lista": price,
                            "disponible": True,
                            "link": f"https://www.golopolis.com.ar/app/?action=detail&itemId={product_id}"
                        })
        except Exception as e:
            print(f"Error fetching Golopolis: {e}")
        return results

    async def search_all(self, query: str, limit_per_store: int = 4) -> List[Dict[str, Any]]:
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._fetch_vtex(session, store_name, domain, query, limit_per_store)
                for store_name, domain in VTEX_STORES
            ]
            tasks.append(self._fetch_monarca(session, query, limit_per_store))
            tasks.append(self._fetch_golopolis(session, query, limit_per_store))
            responses = await asyncio.gather(*tasks)
            all_products = []
            for res in responses:
                all_products.extend(res)

            # Ordenar por precio ascendente
            all_products.sort(key=lambda x: x["precio"])
            return all_products

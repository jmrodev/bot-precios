"""Tests de providers contra fixtures reales capturados de cada mercado (sin red)."""
import json
import pathlib

import pytest

from core.providers import GolopolisProvider, MonarcaProvider, PROVIDERS, VtexProvider

FIXTURES = pathlib.Path(__file__).resolve().parent.parent / "fixtures"


def test_fixtures_existen():
    for nombre in ("vtex_search.json", "monarca_search.json", "golopolis_search.html"):
        assert (FIXTURES / nombre).is_file(), f"falta fixtures/{nombre}"


def test_vtex_parsea_ofertas():
    payload = json.loads((FIXTURES / "vtex_search.json").read_text(encoding="utf-8"))
    provider = VtexProvider("Vea", "www.vea.com.ar")
    ofertas = provider.parse(payload)

    assert ofertas, "el fixture debe producir ofertas"
    primera = ofertas[0]
    assert primera.market == "Vea"
    assert primera.product
    assert primera.price > 0
    assert primera.link.startswith("http")


def test_monarca_parsea_ofertas():
    payload = json.loads((FIXTURES / "monarca_search.json").read_text(encoding="utf-8"))
    ofertas = MonarcaProvider().parse(payload)

    assert ofertas
    assert ofertas[0].market == "Monarca"
    assert ofertas[0].price > 0
    assert ofertas[0].ean  # viene de barcode


def test_golopolis_parsea_html_con_precio_us():
    html = (FIXTURES / "golopolis_search.html").read_text(encoding="utf-8", errors="ignore")
    ofertas = GolopolisProvider().parse(html)

    assert ofertas
    assert ofertas[0].market == "Golopolis"
    # valores exactos del fixture: si "2,565.54" se parseara como formato argentino
    # daría 2.56554 en vez de 2565.54
    assert len(ofertas) == 2
    assert [o.price for o in ofertas] == [3927.47, 2565.54]
    assert ofertas[1].product == "Baño Repostero Georgalos Leche X150g"
    assert ofertas[1].ean == "7790380016687"
    assert ofertas[1].link.endswith("itemId=10121")


def test_vtex_descarta_productos_sin_stock():
    # VTEX devuelve precio residual en SKUs agotados (ej. $34,57 por una yerba de 1 kg)
    payload = [{
        "productName": "Yerba Agotada 1 Kg",
        "brand": "Marca",
        "link": "https://www.vea.com.ar/yerba-agotada/p",
        "items": [{
            "ean": "7790000000001",
            "sellers": [{"commertialOffer": {
                "Price": 34.57, "ListPrice": 2857.0, "AvailableQuantity": 0,
            }}],
        }],
    }]
    assert VtexProvider("Vea", "www.vea.com.ar").parse(payload) == []


def test_parse_respeta_el_limite():
    payload = json.loads((FIXTURES / "vtex_search.json").read_text(encoding="utf-8"))
    assert len(VtexProvider("Vea", "www.vea.com.ar").parse(payload, limit=1)) == 1


def test_payload_invalido_no_explota():
    provider = VtexProvider("Vea", "www.vea.com.ar")
    assert provider.parse(None) == []
    assert provider.parse([]) == []
    assert MonarcaProvider().parse(None) == []
    assert GolopolisProvider().parse("") == []


def test_markets_y_registry():
    from core import MARKETS

    assert MARKETS == ["Carrefour", "Vea", "Día", "Monarca", "Golopolis"]
    assert len(PROVIDERS) == len(MARKETS)

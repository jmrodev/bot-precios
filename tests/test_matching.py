from core.matching import filter_relevant, group_products
from core.models import Offer


def oferta(market, product, price, ean=""):
    return Offer(market=market, product=product, price=price, ean=ean)


def test_agrupa_mismo_ean_entre_mercados():
    offers = [
        oferta("Vea", "Yerba Playadito 500g", 2690, "7793704000881"),
        oferta("Día", "YERBA MATE PLAYADITO X 500 G", 2790, "7793704000881"),
        oferta("Carrefour", "Otra cosa", 1000, "7790000000000"),
    ]
    grupos = group_products(offers)
    comparables = [g for g in grupos if len(g.offers) > 1]
    assert len(comparables) == 1
    assert [o.market for o in comparables[0].offers] == ["Vea", "Día"]
    assert comparables[0].offers[0].price == 2690


def test_sin_ean_agrupa_por_nombre_normalizado():
    offers = [
        oferta("Vea", "Leche La Serenísima 1L", 3000),
        oferta("Día", "leche la serenisima 1l", 3200),
    ]
    grupos = group_products(offers)
    assert len(grupos) == 1
    assert len(grupos[0].offers) == 2


def test_mismo_mercado_dos_veces_deja_la_mas_barata():
    offers = [
        oferta("Vea", "Leche X 1L", 3000, "7790742363107"),
        oferta("Vea", "Leche X 1L promo", 2500, "7790742363107"),
    ]
    grupos = group_products(offers)
    assert len(grupos) == 1
    assert grupos[0].offers[0].price == 2500


def test_orden_premia_productos_comparables():
    offers = [
        oferta("Vea", "Solo en Vea", 100),
        oferta("Vea", "Comparable", 900, "1111111111111"),
        oferta("Día", "Comparable", 800, "1111111111111"),
    ]
    grupos = group_products(offers)
    assert grupos[0].title == "Comparable"


def test_filtro_estricto_descarta_ruido():
    offers = [
        oferta("Carrefour", "Licor Cusenier dulce de leche", 5000),
        oferta("Vea", "Leche La Serenísima 1L", 3000),
    ]
    resultado = filter_relevant(offers, "leche la serenisima")
    assert [o.market for o in resultado] == ["Vea"]


def test_filtro_relaja_si_el_estricto_vacia():
    offers = [oferta("Golopolis", "Natura Girasol X1.5l", 6354)]
    resultado = filter_relevant(offers, "aceite natura")
    assert len(resultado) == 1  # "natura" alcanza cuando no hay mejor opción


def test_filtro_devuelve_todo_si_no_hay_ninguna_coincidencia():
    offers = [oferta("Vea", "Producto raro", 100)]
    assert len(filter_relevant(offers, "zzzz")) == 1

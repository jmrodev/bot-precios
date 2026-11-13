from core.normalize import money, norm, parse_us_price, tokens


def test_norm_quita_acentos_y_minusculas():
    assert norm("Leche La Serenísima 1 L.") == "leche la serenisima 1 l."
    assert norm("  YERBA   Playadito ") == "yerba playadito"


def test_tokens_ignora_palabras_cortas():
    assert tokens("leche la serenisima") == ["leche", "serenisima"]
    assert tokens("p 1") == ["p", "1"]  # si no queda nada util, usa todas


def test_money_formato_argentino():
    assert money(1234.5) == "$1.234,50"
    assert money(2890) == "$2.890,00"
    assert money(1234567.891) == "$1.234.567,89"


def test_parse_us_price_golopolis():
    assert parse_us_price("6,354.42") == 6354.42
    assert parse_us_price("$20,757.25") == 20757.25
    assert parse_us_price("basura") == 0.0


def test_parse_us_price_no_confunde_con_formato_argentino():
    # Golopolis es el único con formato US; dejamos documentado el caso
    assert parse_us_price("3,898.00") == 3898.0

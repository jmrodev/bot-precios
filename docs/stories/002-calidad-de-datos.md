# Story 002 — Calidad de datos: ofertas comprables y moneda correcta

## Contexto
Detectado al rewirear el bot contra `core/` con una búsqueda real (`yerba playa`):

1. **VTEX devuelve precios basura en SKUs agotados.** `Yerba Mate Playadito Con Palo`
   (1 kg) aparecía a **$34,57** con `AvailableQuantity: 0` y `ListPrice: 2857`. El
   precio real no existe porque no se puede comprar.
2. **Golopolis publica precios en formato US** (`6,354.42` = 6354.42). Parsearlo como
   formato argentino da 6.35442: cien mil veces menos.

## Criterios de aceptación (BDD)

### AC1 — Un producto sin stock no es una oferta
- **Given** un payload VTEX con `AvailableQuantity: 0` y `Price: 34.57`
- **When** el provider parsea
- **Then** ese producto no aparece en el resultado

### AC2 — Un producto publicado sí es una oferta
- **Given** un payload VTEX con `AvailableQuantity: 99999` y `Price: 2690`
- **When** el provider parsea
- **Then** aparece con precio `2690`

### AC3 — Precio de Golopolis en formato US
- **Given** el HTML de Golopolis con `$2,565.54`
- **When** se parsea
- **Then** el precio es `2565.54`

### AC4 — El bot no muestra el token en el journal
- **Given** el servicio corriendo con `logging.INFO`
- **When** el bot envía un mensaje a la Bot API
- **Then** `httpx` no escribe la URL con token en el journal (`WARNING` o superior)

## Fuera de alcance
- Normalizar `list_price`/descuentos por mercado (Story 004)
- Promociones bancarias (Story 005)

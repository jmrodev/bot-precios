# Story 001 — Separar el dominio (`core/`) del cliente Telegram

## Contexto
El bot creció a 5 mercados con 3 formatos de datos distintos dentro de un solo
`scraper.py`. Sin separación no hay tests posibles sin red ni Telegram, y agregar
clientes (web, PWA) duplicaría la lógica.

## Decisión
`core/` es el único lugar con lógica de negocio. No conoce Telegram, ni HTTP de
entrada, ni FastAPI. Cada mercado es un provider con la misma interfaz:

```python
provider.parse(payload, limit) -> list[Offer]     # puro, testeable con fixtures
await provider.fetch(session, query, limit)       # red
```

## Criterios de aceptación (BDD)

### AC1 — Un solo tipo de dato
- **Given** ofertas obtenidas de Carrefour, Monarca y Golopolis
- **When** se leen sus campos
- **Then** las tres son `Offer` con `market`, `product`, `brand`, `ean`, `price`,
  `list_price`, `available`, `link`

### AC2 — Tests sin red
- **Given** los fixtures `fixtures/vtex_search.json`, `fixtures/monarca_search.json`
  y `fixtures/golopolis_search.html`
- **When** corre `pytest`
- **Then** los providers parsean sin abrir conexiones

### AC3 — Precio de Golopolis en formato US
- **Given** el HTML de Golopolis con `$6,354.42`
- **When** se parsea
- **Then** el precio es `6354.42` (no `6.35442`)

### AC4 — Comparación por producto
- **Given** dos ofertas del mismo EAN en mercados distintos
- **When** se agrupan
- **Then** forman un único `ProductGroup` con ambas ofertas ordenadas por precio

### AC5 — Un mercado caído no rompe la búsqueda
- **Given** un provider que lanza excepción
- **When** corre `search_all`
- **Then** se devuelven las ofertas de los demás mercados

### AC6 — Comportamiento del bot intacto
- **Given** el bot desplegado
- **When** se busca un producto
- **Then** responde con la misma vista comparada que antes del refactor

## Fuera de alcance
- API HTTP (Story 002)
- Persistencia (Story 003)

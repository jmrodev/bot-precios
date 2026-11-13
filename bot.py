import os
import html
import logging
import uuid
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from core import MARKETS, filter_relevant, group_products, money, search_all

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
# httpx loguea la URL completa de la Bot API, token incluido: no lo queremos en el journal
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

LIMIT_PER_STORE = 6
MAX_BLOCKS = 8
MAX_CACHE = 50
CACHE = {}


# ---------- utilidades de texto ----------

def _esc(text: str) -> str:
    return html.escape(text or "")


def _link(label: str, url: str) -> str:
    name = _esc(label)
    if url:
        return f'<a href="{html.escape(url)}">{name}</a>'
    return name


# ---------- render ----------

def _render_comparison(groups, query) -> str:
    lines = [f"📊 <b>{_esc(query)}</b>"]
    lines.append(f"<i>{len(groups)} producto(s) · precio por mercado</i>")

    for g in groups[:MAX_BLOCKS]:
        lines.append("")
        lines.append(f"<b>{_esc(g.title)}</b>")
        for i, o in enumerate(g.offers):
            mark = "🏆" if i == 0 else "▫️"
            lines.append(f"{mark} <b>{money(o.price)}</b> · {_link(o.market, o.link)}")

    if len(groups) > MAX_BLOCKS:
        lines.append("")
        lines.append(f"<i>… y {len(groups) - MAX_BLOCKS} producto(s) más. Afiná la búsqueda.</i>")

    lines.append("")
    lines.append("🏆 = más barato · tocá el mercado para abrir el producto")
    return "\n".join(lines)


def _render_by_market(offers, query) -> str:
    por_mercado = {}
    for o in offers:
        por_mercado.setdefault(o.market, []).append(o)

    lines = [f"🏪 <b>{_esc(query)}</b> por mercado"]
    for market in MARKETS:
        items = sorted(por_mercado.get(market, []), key=lambda x: x.price)
        if not items:
            continue
        lines.append("")
        lines.append(f"<b>{_esc(market)}</b>")
        for o in items[:5]:
            lines.append(f"▫️ <b>{money(o.price)}</b> · {_link(o.product[:70], o.link)}")
    return "\n".join(lines)


def _render_top(groups, query, n=5) -> str:
    lines = [f"💰 <b>{_esc(query)}</b> — los {n} más baratos"]
    flat = []
    for g in groups:
        for o in g.offers:
            flat.append((o, g.title))
    flat.sort(key=lambda x: x[0].price)
    for o, title in flat[:n]:
        lines.append("")
        lines.append(f"<b>{money(o.price)}</b> · {_link(o.market, o.link)}")
        lines.append(f"   {_esc(title)[:80]}")
    return "\n".join(lines)


def _buttons(key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("💰 Top 5", callback_data=f"top:{key}"),
        InlineKeyboardButton("🏪 Por mercado", callback_data=f"market:{key}"),
        InlineKeyboardButton("📊 Por producto", callback_data=f"prod:{key}"),
    ]])


# ---------- handlers ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name if update.effective_user else "Hola"
    msg = (
        f"👋 ¡Hola, {user_name}!\n\n"
        "Soy <b>ComparaPrecios AR</b> 🇦🇷, tu comparador de precios de supermercados 🛒\n\n"
        "Comandos disponibles:\n"
        "• <code>/p &lt;producto&gt;</code> : busca precios en tiempo real (ej. <code>/p leche la serenisima</code>)\n"
        "• También podés escribirme el producto o marca directamente.\n\n"
        f"Consultando: {', '.join('<b>' + _esc(m) + '</b>' for m in MARKETS)} (en tiempo real).\n\n"
        "Cada resultado trae los mismos productos comparados entre mercados, con el más barato marcado 🏆."
    )
    await update.message.reply_text(msg, parse_mode="HTML")


async def buscar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        query = " ".join(context.args).strip()
    else:
        query = (update.message.text or "").strip()
        if query.startswith("/"):
            query = query.lstrip("/p").strip()

    if not query:
        await update.message.reply_text(
            "Escribí el nombre de un producto. Ej: <code>/p yerba playadito</code>",
            parse_mode="HTML"
        )
        return

    status_msg = await update.message.reply_text(
        f"🔍 Buscando precios de <b>{_esc(query)}</b> en {len(MARKETS)} mercados...",
        parse_mode="HTML"
    )

    try:
        results = await search_all(query, limit=LIMIT_PER_STORE)
        results = filter_relevant(results, query)

        if not results:
            await status_msg.edit_text(
                f"No encontré resultados para <b>{_esc(query)}</b> en ningún mercado.",
                parse_mode="HTML"
            )
            return

        groups = group_products(results)

        key = uuid.uuid4().hex[:10]
        CACHE[key] = {"query": query, "results": results, "groups": groups}
        if len(CACHE) > MAX_CACHE:
            CACHE.pop(next(iter(CACHE)))

        await status_msg.edit_text(
            _render_comparison(groups, query),
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=_buttons(key),
        )

    except Exception as e:
        logger.error(f"Error procesando búsqueda: {e}")
        await status_msg.edit_text("Ocurrió un error al consultar las tiendas. Intentá nuevamente en unos instantes.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    call = update.callback_query
    await call.answer()

    try:
        action, key = call.data.split(":", 1)
    except ValueError:
        return

    data = CACHE.get(key)
    if not data:
        await call.edit_message_text("La búsqueda expiró. Repetila con /p.")
        return

    query, results, groups = data["query"], data["results"], data["groups"]

    if action == "top":
        text = _render_top(groups, query)
    elif action == "market":
        text = _render_by_market(results, query)
    else:
        text = _render_comparison(groups, query)

    try:
        await call.edit_message_text(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=_buttons(key),
        )
    except Exception as e:
        # Telegram devuelve error si el texto es idéntico al actual (botón repetido)
        logger.info(f"Edición sin cambios: {e}")


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        token_path = os.path.join(os.path.dirname(__file__), "token.txt")
        if os.path.exists(token_path):
            with open(token_path, "r") as f:
                token = f.read().strip()

    if not token:
        print("\n[!] ERROR: No se encontró TELEGRAM_BOT_TOKEN.")
        print("    Define la variable de entorno o escribe el token en 'token.txt'.\n")
        return

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("p", buscar_handler))
    app.add_handler(CommandHandler("precio", buscar_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), buscar_handler))

    print(f"🤖 ComparaPrecios AR iniciado (mercados: {', '.join(MARKETS)}). Presiona Ctrl+C para detener.")
    app.run_polling()


if __name__ == "__main__":
    main()

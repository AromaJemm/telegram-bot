import importlib
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from apscheduler.schedulers.background import BackgroundScheduler

from config import BOT_TOKEN, WAREHOUSE_FILE
from catalog import CATALOG

# ------------------------
# СКЛАД
# ------------------------

WAREHOUSE = {}

def load_warehouse():
    global WAREHOUSE

    df = pd.read_excel(WAREHOUSE_FILE)
    WAREHOUSE = {}

    for _, row in df.iterrows():
        product_id = str(row["product_id"]).strip()
        WAREHOUSE[product_id] = {
            "quantity": int(row["quantity"]),
            "active": int(row["active"]),
        }

    print("Склад обновлён")


def product_available(product_id: str) -> bool:
    data = WAREHOUSE.get(product_id)
    if not data:
        return False
    return data["active"] == 1 and data["quantity"] > 0


# ------------------------
# КАТАЛОГ
# ------------------------

def get_product(module_path):
    module = importlib.import_module(module_path)
    return module.PRODUCT


# ------------------------
# HANDLERS
# ------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []

    for key, section in CATALOG.items():
        keyboard.append(
            [InlineKeyboardButton(section["title"], callback_data=f"cat:{key}")]
        )

    await update.message.reply_text(
        "Выберите категорию:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def open_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category_key = query.data.split(":")[1]
    section = CATALOG[category_key]

    keyboard = []

    for item_path in section["items"]:
        product = get_product(item_path)

        if product_available(product["id"]):
            keyboard.append(
                [InlineKeyboardButton(product["name"], callback_data=f"prod:{item_path}")]
            )

    if not keyboard:
        await query.edit_message_text("В этой категории пока нет доступных товаров.")
        return

    await query.edit_message_text(
        section["title"],
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def open_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    module_path = query.data.split(":")[1]
    product = get_product(module_path)

    text = (
        f"*{product['name']}*\n\n"
        f"{product['properties']}\n\n"
        f"*Применение:*\n{product['usage']}\n\n"
        f"*Безопасность:*\n{product['safety']}\n\n"
        f"*Характеристики:*\n{product['tech']}\n\n"
        f"Цена: {product['price_bot']} ₽"
    )

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
    )


# ------------------------
# MAIN
# ------------------------

def main():
    load_warehouse()

    scheduler = BackgroundScheduler()
    scheduler.add_job(load_warehouse, "interval", hours=12)
    scheduler.start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(open_category, pattern="^cat:"))
    app.add_handler(CallbackQueryHandler(open_product, pattern="^prod:"))

    app.run_polling()


if __name__ == "__main__":
    main()

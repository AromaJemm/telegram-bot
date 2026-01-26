import importlib
import pandas as pd
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from apscheduler.schedulers.background import BackgroundScheduler
import re
import os
import requests

from catalog import CATALOG

# ------------------------
# ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ
# ------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WAREHOUSE_FILE_LINK = os.environ.get("WAREHOUSE_FILE_LINK")

# ------------------------
# СКЛАД
# ------------------------
WAREHOUSE = {}

def load_warehouse():
    global WAREHOUSE
    try:
        resp = requests.get(WAREHOUSE_FILE_LINK)
        resp.raise_for_status()
        df = pd.read_excel(BytesIO(resp.content))
    except Exception as e:
        print(f"Ошибка загрузки склада: {e}")
        return

    WAREHOUSE = {}
    for _, row in df.iterrows():
        product_id = str(row.get("product_id", "")).strip()
        try:
            quantity = int(row.get("quantity", 0))
        except:
            quantity = 0
        try:
            active = int(row.get("active", 0))
        except:
            active = 0

        if product_id:
            WAREHOUSE[product_id] = {"quantity": quantity, "active": active}

    print("Склад обновлён")

def product_available(product_id: str) -> bool:
    data = WAREHOUSE.get(product_id)
    if not data:
        return False
    return data["active"] == 1 and data["quantity"] > 0

# ------------------------
# КАТАЛОГ
# ------------------------
PRODUCT_CACHE = {}

def get_product(module_path):
    if module_path in PRODUCT_CACHE:
        return PRODUCT_CACHE[module_path]
    try:
        module = importlib.import_module(module_path)
        product = module.PRODUCT
        PRODUCT_CACHE[module_path] = product
        return product
    except Exception as e:
        print(f"Ошибка импорта {module_path}: {e}")
        return None

# ------------------------
# УТИЛИТЫ
# ------------------------
def escape_md(text: str) -> str:
    if not text:
        return ""
    escape_chars = r"\_*[]()~`>#+-=|{}.!-"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)

def make_welcome_keyboard():
    buttons = [
        [InlineKeyboardButton("🛒 Каталог товаров", callback_data="home")],
        [InlineKeyboardButton("🤖 Интерактивный помощник", callback_data="assistant")],
        [InlineKeyboardButton("🛍 Корзина", callback_data="cart")],
        [InlineKeyboardButton("📞 Связь с оператором", callback_data="operator")],
    ]
    return InlineKeyboardMarkup(buttons)

# ------------------------
# HANDLERS
# ------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие с фото и пояснением кнопок"""
    welcome_text = (
        "👋 Добро пожаловать в Scentori!\n\n"
        "Мы помогаем подобрать ароматы и собрать уникальные композиции под ваше настроение.\n\n"
        "Ниже — кнопки для навигации:"
    )

    photo_path = "images/welcome.jpg"
    try:
        with open(photo_path, "rb") as photo_file:
            await update.message.reply_photo(
                photo=InputFile(photo_file),
                caption=welcome_text,
                parse_mode="MarkdownV2"
            )
    except FileNotFoundError:
        await update.message.reply_text(
            welcome_text,
            parse_mode="MarkdownV2"
        )

    description_text = (
        "🛒 *Каталог товаров* — выберите аромат и изучите ассортимент.\n"
        "🤖 *Интерактивный помощник* — круглосуточная помощь для поиска идеального аромата.\n"
        "🛍 *Корзина* — здесь собираются ваши выбранные товары перед оформлением заказа.\n"
        "📞 *Связь с оператором* — для консультации и отправки заказа через Яндекс.Доставку или самовывоз."
    )

    await update.message.reply_text(
        description_text,
        reply_markup=make_welcome_keyboard(),
        parse_mode="MarkdownV2"
    )

async def go_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await start(update, context)

async def open_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category_key = query.data.split(":")[1]
    section = CATALOG.get(category_key)
    if not section:
        await query.edit_message_text("Категория не найдена.")
        return

    available_products = []
    for item_path in section["items"]:
        product = get_product(item_path)
        if product and product_available(product["id"]):
            available_products.append(product)

    available_products.sort(key=lambda p: p["name"])

    keyboard = [[InlineKeyboardButton(p["name"], callback_data=f"prod:{p['id']}:{category_key}")]
                for p in available_products]
    keyboard.append([InlineKeyboardButton("На главную", callback_data="home")])

    if not available_products:
        await query.edit_message_text(
            "В этой категории пока нет доступных товаров.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await query.edit_message_text(
        escape_md(section["title"]),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="MarkdownV2"
    )

async def open_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    product_id = parts[1]
    category_key = parts[2] if len(parts) > 2 else None

    product = None
    for p in PRODUCT_CACHE.values():
        if p["id"] == product_id:
            product = p
            break

    if not product:
        await query.edit_message_text("Товар не найден.")
        return

    text = (
        f"*{escape_md(product['name'])}*\n\n"
        f"{escape_md(product.get('properties', ''))}\n\n"
        f"*Применение:*\n{escape_md(product.get('usage', ''))}\n\n"
        f"*Безопасность:*\n{escape_md(product.get('safety', ''))}\n\n"
        f"*Характеристики:*\n{escape_md(product.get('tech', ''))}\n\n"
        f"Цена: {product.get('price_bot', '—')} ₽\n\n"
        "_Если вы хотите более глубоко исследовать ароматы, "
        "мы сделали интерактивного помощника, который работает для вас круглосуточно. "
        "Для доступа выберите кнопку 'Интерактивный помощник' в главном меню._"
    )

    keyboard = []
    if category_key:
        keyboard.append([InlineKeyboardButton("Назад", callback_data=f"cat:{category_key}")])
    keyboard.append([InlineKeyboardButton("На главную", callback_data="home")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    image_path = product.get("photo")
    if image_path:
        try:
            with open(image_path, "rb") as f:
                await query.edit_message_media(
                    media=InputMediaPhoto(media=f, caption=text, parse_mode="MarkdownV2"),
                    reply_markup=reply_markup
                )
        except Exception as e:
            print(f"Ошибка отображения фото: {e}")
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode="MarkdownV2"
            )
    else:
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode="MarkdownV2"
        )

async def assistant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🤖 Интерактивный помощник готов помогать вам в подборе ароматов.\n"
        "Выберите категорию или товар для рекомендаций.",
        reply_markup=make_welcome_keyboard()
    )

async def cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🛍 Ваша корзина пока пуста.\n"
        "Вы можете добавлять товары из каталога.",
        reply_markup=make_welcome_keyboard()
    )

async def operator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📞 Чтобы оформить заказ или уточнить детали, свяжитесь с оператором.\n"
        "Мы используем Яндекс.Доставку или самовывоз с двух адресов.",
        reply_markup=make_welcome_keyboard()
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
    app.add_handler(CallbackQueryHandler(go_home, pattern="^home$"))
    app.add_handler(CallbackQueryHandler(open_category, pattern="^cat:"))
    app.add_handler(CallbackQueryHandler(open_product, pattern="^prod:"))
    app.add_handler(CallbackQueryHandler(assistant, pattern="^assistant$"))
    app.add_handler(CallbackQueryHandler(cart, pattern="^cart$"))
    app.add_handler(CallbackQueryHandler(operator, pattern="^operator$"))

    app.run_polling()

if __name__ == "__main__":
    main()

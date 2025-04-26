import os
import telebot
from flask import Flask, request
from threading import Thread
import time
import requests
import logging
from waitress import serve
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from products import PRODUCTS

# --- Настройка логов ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

app = Flask(__name__)
token = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(token)
WEBHOOK_URL = f"https://{os.getenv('RENDER_SERVICE_NAME')}.onrender.com/{token}"
PORT = int(os.getenv("PORT", 8080))

# Настройки почты (Mail.ru)
SMTP_SERVER = 'smtp.mail.ru'
SMTP_PORT = 587
EMAIL_ADDRESS = '5049190@mail.ru'
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')  # Пароль приложения из Mail.ru

# Хранение данных пользователя
user_data = {}

# --- Автопробуждение (не дает Render усыпить бота) ---
def ping_server():
    while True:
        try:
            # Пинг Render и Telegram
            requests.get(f"https://{os.getenv('RENDER_SERVICE_NAME')}.onrender.com", timeout=10)
            requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            logging.info("🔄 Пинг выполнен (бот активен)")
        except Exception as e:
            logging.error(f"❌ Ошибка пинга: {e}")
        time.sleep(295)  # Каждые 5 минут

# --- Главное меню ---
def main_menu_markup():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = ["Наш сайт 🌐", "Инструкции 📖", "Написать нам ✉️"]
    markup.add(*[telebot.types.KeyboardButton(btn) for btn in buttons])
    return markup

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "🌿 Добро пожаловать! Я ваш помощник по ароматерапии. Выберите действие:",
        reply_markup=main_menu_markup()
    )

# --- Обработка кнопок ---
@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    try:
        if message.text == "Наш сайт 🌐":
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("Открыть сайт", url="https://jemmfashion.ru"))
            bot.send_message(message.chat.id, "🌱 Наш сайт:", reply_markup=markup)

        elif message.text == "Инструкции 📖":
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            for product_name in PRODUCTS.keys():
                markup.add(telebot.types.KeyboardButton(product_name))
            markup.add(telebot.types.KeyboardButton("Назад 🔙"))
            bot.send_message(message.chat.id, "Выберите продукт:", reply_markup=markup)

        elif message.text == "Назад 🔙":
            bot.send_message(message.chat.id, "Главное меню:", reply_markup=main_menu_markup())

        elif message.text in PRODUCTS:
            product = PRODUCTS[message.text]
            if "image" in product:
                bot.send_photo(
                    message.chat.id,
                    photo=product["image"],
                    caption=product["description"],
                    parse_mode="HTML",
                    reply_markup=main_menu_markup()
                )
            else:
                bot.send_message(
                    message.chat.id,
                    product["description"],
                    parse_mode="HTML",
                    reply_markup=main_menu_markup()
                )

        elif message.text == "Написать нам ✉️":
            msg = bot.send_message(
                message.chat.id,
                "Как к вам обращаться? (напишите имя):",
                reply_markup=telebot.types.ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(msg, process_name_step)

    except Exception as e:
        logging.error(f"❌ Ошибка: {e}")
        bot.send_message(message.chat.id, "⚠️ Ошибка. Попробуйте позже.", reply_markup=main_menu_markup())

# --- Обработка сообщений (имя → телефон → вопрос) ---
def process_name_step(message):
    try:
        chat_id = message.chat.id
        user_data[chat_id] = {'name': message.text.strip()}
        msg = bot.send_message(chat_id, "📞 Ваш телефон для связи:")
        bot.register_next_step_handler(msg, process_phone_step)
    except Exception as e:
        logging.error(f"❌ Ошибка имени: {e}")
        bot.send_message(message.chat.id, "⚠️ Ошибка. Начните заново.", reply_markup=main_menu_markup())

def process_phone_step(message):
    try:
        chat_id = message.chat.id
        user_data[chat_id]['phone'] = message.text.strip()
        msg = bot.send_message(chat_id, "📝 Ваш вопрос:")
        bot.register_next_step_handler(msg, process_question_step)
    except Exception as e:
        logging.error(f"❌ Ошибка телефона: {e}")
        bot.send_message(message.chat.id, "⚠️ Ошибка. Начните заново.", reply_markup=main_menu_markup())

def process_question_step(message):
    try:
        chat_id = message.chat.id
        user_data[chat_id]['question'] = message.text.strip()
        
        # Отправка email
        send_email(
            f"Новый запрос от {user_data[chat_id]['name']}\n"
            f"Телефон: {user_data[chat_id]['phone']}\n"
            f"Вопрос: {user_data[chat_id]['question']}"
        )
        
        bot.send_message(
            chat_id,
            "✅ Мы свяжемся с вами в течение 30 минут!",
            reply_markup=main_menu_markup()
        )
    except Exception as e:
        logging.error(f"❌ Ошибка вопроса: {e}")
        bot.send_message(message.chat.id, "❌ Ошибка отправки.", reply_markup=main_menu_markup())
    finally:
        if chat_id in user_data:
            del user_data[chat_id]

# --- Отправка email ---
def send_email(text):
    try:
        msg = MIMEMultipart()
        msg['From'] = formataddr(('Telegram Bot', EMAIL_ADDRESS))
        msg['To'] = EMAIL_ADDRESS
        msg['Subject'] = 'Новый запрос с бота'
        msg.attach(MIMEText(text, 'plain'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        logging.info('✅ Email отправлен')
        return True
    except Exception as e:
        logging.error(f'❌ Ошибка отправки email: {e}')
        return False

# --- Запуск Flask ---
def run_flask():
    serve(app, host="0.0.0.0", port=PORT)

# --- Вебхуки ---
@app.route("/")
def home():
    return "Бот активен!"

@app.route(f"/{token}", methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_data = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

# --- Запуск ---
if __name__ == "__main__":
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=WEBHOOK_URL)
        Thread(target=ping_server, daemon=True).start()  # Автопробуждение
        run_flask()
    except Exception as e:
        logging.critical(f"💥 Критическая ошибка: {e}")
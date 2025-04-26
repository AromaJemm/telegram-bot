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
from products import PRODUCTS  # Импорт инструкций по продуктам

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

# Настройки почты (ваши данные)
SMTP_SERVER = 'smtp.mail.ru'  # Для mail.ru
SMTP_PORT = 587
EMAIL_ADDRESS = '5049190@mail.ru'
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')  # Пароль от почты (добавьте в Render)

# Для временного хранения данных пользователя
user_data = {}

# --- Главное меню ---
def main_menu_markup():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        "Наш сайт 🌐", 
        "Инструкции по продуктам 📖", 
        "Написать нам ✉️"
    ]
    markup.add(*[telebot.types.KeyboardButton(btn) for btn in buttons])
    return markup

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "🌿 Добро пожаловать! Я помогу вам с ароматерапией. Выберите действие:",
        reply_markup=main_menu_markup()
    )

# --- Обработка кнопок ---
@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    try:
        if message.text == "Наш сайт 🌐":
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(
                text="Перейти на сайт", 
                url="https://jemmfashion.ru"
            ))
            bot.send_message(
                message.chat.id,
                "🌱 Наш сайт с полным ассортиментом:",
                reply_markup=markup
            )

        elif message.text == "Инструкции по продуктам 📖":
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            for product_name in PRODUCTS.keys():
                markup.add(telebot.types.KeyboardButton(product_name))
            markup.add(telebot.types.KeyboardButton("Назад 🔙"))
            bot.send_message(
                message.chat.id,
                "🌿 Выберите продукт:",
                reply_markup=markup
            )

        elif message.text == "Назад 🔙":
            bot.send_message(
                message.chat.id,
                "Главное меню:",
                reply_markup=main_menu_markup()
            )

        elif message.text in PRODUCTS:
            bot.send_message(
                message.chat.id,
                PRODUCTS[message.text],
                parse_mode="HTML",
                reply_markup=main_menu_markup()  # Кнопка "Назад" здесь
            )

        elif message.text == "Написать нам ✉️":
            msg = bot.send_message(
                message.chat.id,
                "Как к вам обращаться? (напишите имя):",
                reply_markup=telebot.types.ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(msg, process_name_step)

        else:
            bot.send_message(
                message.chat.id,
                "❌ Неизвестная команда. Пожалуйста, используйте меню.",
                reply_markup=main_menu_markup()
            )

    except Exception as e:
        logging.error(f"❌ Ошибка: {e}")
        bot.send_message(
            message.chat.id,
            "⚠️ Произошла ошибка. Попробуйте позже.",
            reply_markup=main_menu_markup()
        )

# --- Шаги обработки сообщения ---
def process_name_step(message):
    try:
        chat_id = message.chat.id
        user_data[chat_id] = {'name': message.text.strip()}
        
        msg = bot.send_message(
            chat_id,
            "📞 Напишите ваш телефон для связи:"
        )
        bot.register_next_step_handler(msg, process_phone_step)
        
    except Exception as e:
        logging.error(f"❌ Ошибка ввода имени: {e}")
        bot.send_message(
            message.chat.id,
            "⚠️ Ошибка. Начните заново, нажав 'Написать нам ✉️'.",
            reply_markup=main_menu_markup()
        )

def process_phone_step(message):
    try:
        chat_id = message.chat.id
        phone = message.text.strip()
        
        if not phone:
            msg = bot.send_message(
                chat_id,
                "❌ Телефон не может быть пустым. Введите еще раз:"
            )
            bot.register_next_step_handler(msg, process_phone_step)
            return
            
        user_data[chat_id]['phone'] = phone
        
        msg = bot.send_message(
            chat_id,
            "📝 Напишите ваш вопрос:"
        )
        bot.register_next_step_handler(msg, process_question_step)
        
    except Exception as e:
        logging.error(f"❌ Ошибка ввода телефона: {e}")
        bot.send_message(
            message.chat.id,
            "⚠️ Ошибка. Начните заново, нажав 'Написать нам ✉️'.",
            reply_markup=main_menu_markup()
        )

def process_question_step(message):
    try:
        chat_id = message.chat.id
        question = message.text.strip()
        
        if not question:
            msg = bot.send_message(
                chat_id,
                "❌ Вопрос не может быть пустым. Введите еще раз:"
            )
            bot.register_next_step_handler(msg, process_question_step)
            return
            
        user_data[chat_id]['question'] = question
        
        # Формируем текст письма
        name = user_data[chat_id]['name']
        phone = user_data[chat_id]['phone']
        email_text = f"""
        Новый запрос от пользователя:
        Имя: {name}
        Телефон: {phone}
        Вопрос: {question}
        """
        
        # Отправляем email
        if send_email(email_text):
            bot.send_message(
                chat_id,
                "✅ Мы свяжемся с вами в течение 30 минут!",
                reply_markup=main_menu_markup()
            )
        else:
            bot.send_message(
                chat_id,
                "❌ Ошибка отправки. Попробуйте позже.",
                reply_markup=main_menu_markup()
            )
            
    except Exception as e:
        logging.error(f"❌ Ошибка ввода вопроса: {e}")
        bot.send_message(
            message.chat.id,
            "⚠️ Ошибка. Начните заново, нажав 'Написать нам ✉️'.",
            reply_markup=main_menu_markup()
        )
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

# --- Автопробуждение (чтобы сервер не "засыпал") ---
def ping_server():
    while True:
        try:
            requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
            logging.info("✅ Связь с Telegram установлена")
        except Exception as e:
            logging.error(f"❌ Нет связи с Telegram: {e}")
        
        try:
            requests.get(f"https://{os.getenv('RENDER_SERVICE_NAME')}.onrender.com", timeout=5)
            logging.info("🔄 Пинг отправлен")
        except Exception as e:
            logging.error(f"❌ Ошибка пинга: {e}")
        
        time.sleep(300)  # Пауза 5 минут

# --- Запуск Flask ---
def run_flask():
    serve(app, host="0.0.0.0", port=PORT)

# --- Вебхуки ---
@app.route("/")
def home():
    return "Бот активен! Мониторинг: UptimeRobot + Render"

@app.route(f"/{token}", methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        try:
            json_data = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_data)
            bot.process_new_updates([update])
            return "OK", 200
        except Exception as e:
            logging.error(f"❌ Ошибка обработки JSON: {e}")
            return "Bad Request", 400
    return "Forbidden", 403

# --- Запуск бота ---
if __name__ == "__main__":
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=WEBHOOK_URL)
        Thread(target=ping_server).start()  # Запускаем автопробуждение
        run_flask()
    except Exception as e:
        logging.critical(f"💥 Критическая ошибка: {e}")
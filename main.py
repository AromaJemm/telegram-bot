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
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')  # Пароль от почты (установите в Render)

# Глобальный словарь для временного хранения данных пользователя
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
                reply_markup=main_menu_markup()
            )

        elif message.text == "Написать нам ✉️":
            msg = bot.send_message(
                message.chat.id,
                "Как к вам обращаться? (напишите имя):",
                reply_markup=telebot.types.ReplyKeyboardRemove()  # Убираем клавиатуру
            )
            bot.register_next_step_handler(msg, process_name_step)  # Переход к следующему шагу

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

# --- Шаг 1: Получение имени ---
def process_name_step(message):
    try:
        chat_id = message.chat.id
        user_data[chat_id] = {'name': message.text.strip()}  # Сохраняем имя
        
        msg = bot.send_message(
            chat_id,
            "📞 Напишите ваш телефон для обратной связи:"
        )
        bot.register_next_step_handler(msg, process_phone_step)  # Переход к шагу с телефоном
        
    except Exception as e:
        logging.error(f"❌ Ошибка ввода имени: {e}")
        bot.send_message(
            message.chat.id,
            "⚠️ Ошибка. Начните заново, нажав 'Написать нам ✉️'.",
            reply_markup=main_menu_markup()
        )

# --- Шаг 2: Получение телефона ---
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
            
        user_data[chat_id]['phone'] = phone  # Сохраняем телефон
        
        msg = bot.send_message(
            chat_id,
            "📝 Напишите ваш вопрос:"
        )
        bot.register_next_step_handler(msg, process_question_step)  # Переход к шагу с вопросом
        
    except Exception as e:
        logging.error(f"❌ Ошибка ввода телефона: {e}")
        bot.send_message(
            message.chat.id,
            "⚠️ Ошибка. Начните заново, нажав 'Написать нам ✉️'.",
            reply_markup=main_menu_markup()
        )

# --- Шаг 3: Получение вопроса и отправка email ---
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
            
        user_data[chat_id]['question'] = question  # Сохраняем вопрос
        
        # Формируем текст письма
        name = user_data[chat_id]['name']
        phone = user_data[chat_id]['phone']
        email_text = f"""
        Новый запрос от пользователя:
        Имя: {name}
        Телефон: {phone}
        Вопрос: {question}
        """
        
        # Отправляем email (ваша функция)
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
            del user_data[chat_id]  # Очищаем данные

# --- Функция отправки email ---
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

# --- Автопробуждение и вебхуки --- (оставьте ваш исходный код)
# ... (как у вас было)

if __name__ == "__main__":
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=WEBHOOK_URL)
        Thread(target=ping_server).start()
        run_flask()
    except Exception as e:
        logging.critical(f"💥 Критическая ошибка: {e}")
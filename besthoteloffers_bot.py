"""
Главный скрипт бота besthoteloffers_bot.py
"""

import config
import telebot

bot = telebot.TeleBot(config.BOT_TOKEN)


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.send_message(message.from_user.id, 'Привет! Чем могу помочь?')


@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    if message.text.lower() == 'привет':
        bot.send_message(message.from_user.id, 'Привет! 👋\nПока я умею столько. Но меня продолжают кодить. 😉')
    else:
        bot.send_message(message.from_user.id, 'Я тебя не понимаю. 🤷\nНапиши "Привет".')


bot.infinity_polling()

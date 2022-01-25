"""
Главный скрипт бота besthoteloffers_bot.py
Содержит основную логику работы бота.
"""

import telebot
from telebot.types import Message, CallbackQuery
from loguru import logger

import bot_db
from config import BOT_TOKEN
# import requests
from commands import highprice, lowprice, bestdeal, history

logger.add('Log/debug.log', encoding='utf-8')

# req = requests.get('', timeout=(1, 3))

bot = telebot.TeleBot(BOT_TOKEN)

# Проверка корректного подключения к Telegram Bot API
bot_info = bot.get_me()
logger.info((f"""
    ID бота: {bot_info.id}, 
    Название бота: {bot_info.first_name}, 
    Пользователь: {bot_info.username}, 
    Подключение: {bot_info.is_bot}"""))

# Подключаемся к БД
bot_db.init_db()


@bot.message_handler(commands=['start'])
@logger.catch
def command_start(message: Message) -> None:
    """
    Функция-обработчик команды start, выводит приветственное сообщение

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    send_message_first_start = (f"""
<b>Приветствую  {message.from_user.first_name} {message.from_user.last_name}!

Я - Best Hotel Offers Bot.</b>
Я умею находить и выводить лучшие отели мира,
в любом городе, по твоим запросам.

Меня ещё разрабатывают, но я кое-что умею.
Для начала напиши "Привет".""")

    send_message_next_starts = (f"""
<b>С возвращением  {message.from_user.first_name} {message.from_user.last_name}!</b>

Похоже, ты решил начать заново?
Что ж, давай начнём. Выбери команду или напиши "Привет".""")

    if not bot_db.user_exists(message.from_user.id):
        bot_db.add_user(
            user_id=message.from_user.id,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            date=message.date
        )
        bot.send_message(message.from_user.id, send_message_first_start, parse_mode='html')
    else:
        bot.send_message(message.from_user.id, send_message_next_starts, parse_mode='html')

    bot_db.add_message(
        user_id=message.from_user.id,
        command=message.text,
        date=message.date
    )


@bot.message_handler(commands=['help'])
@logger.catch
def command_help(message: Message) -> None:
    bot.send_message(message.from_user.id, 'Извини, но данная команда пока в разработке.')
    # TODO дописать функцию


@bot.message_handler(commands=['reset'])
@logger.catch
def command_reset(message: Message) -> None:
    bot.send_message(message.from_user.id, 'Извини, но данная команда пока в разработке.')
    # TODO дописать функцию


@bot.message_handler(commands=['settings'])
@logger.catch
def command_settings(message: Message) -> None:
    bot.send_message(message.from_user.id, 'Извини, но данная команда пока в разработке.')
    # TODO дописать функцию


@bot.message_handler(commands=['lowprice', 'highprice', 'bestdeal', 'history'])
@logger.catch
def search_commands(message: Message) -> None:
    """
    Функция-обработчик команд /lowprice, /highprice, /bestdeal, /history

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    match message.text:
        case '/lowprice':
            # TODO дописать функцию
            bot.send_message(message.from_user.id, 'Извини, но данная команда пока в разработке.')
        case '/highprice':
            # TODO дописать функцию
            bot.send_message(message.from_user.id, 'Извини, но данная команда пока в разработке.')
        case '/bestdeal':
            # TODO дописать функцию
            bot.send_message(message.from_user.id, 'Извини, но данная команда пока в разработке.')
        case '/history':
            history.req_period(bot=bot, message=message)
            bot_db.add_message(
                user_id=message.from_user.id,
                message=message.text,
                date=message.date
            )


@bot.message_handler(content_types=['text'])
@logger.catch
def get_text_messages(message: Message) -> None:
    """
    Функция get_text_message, выполняет различные действия в зависимости
    от сообщения пользователя.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    if message.text.lower() == 'привет':
        bot.send_message(message.from_user.id, 'Привет! 👋\nПока я умею столько. Но меня продолжают кодить. 😉')
    else:
        bot.send_message(message.from_user.id, 'Я тебя не понимаю. 🤷\nНапиши "Привет".')

    bot_db.add_message(
        user_id=message.from_user.id,
        message=message.text,
        date=message.date
    )


@bot.callback_query_handler(func=lambda call: True)
@logger.catch
def callback_query(call: CallbackQuery) -> None:
    """
    Функция-обработчик нажатий на кнопки клавиатуры

    Args:
        call (CallbackQuery): Принимает объект-CallbackQuery от Telegram
    """
    match call.data:
        case 'history_day' | 'history_week' | 'history_month' | 'history_all':
            history.get_history(bot=bot, call=call)


logger.info('Бот в работе')
bot.infinity_polling()

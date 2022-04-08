"""
Модуль, описывающий команду бота history.
Содержит функции и методы для этой команды.
"""

from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

import bot_db


def req_period(bot: TeleBot, message: Message) -> None:
    """
    Функция-обработчик команды /history.
    Создаёт и выводит клавиатуру для выбора периода истории

    Args:
        bot (TeleBot): Принимает объект
        message (Message): Принимает объект-сообщение от Telegram
    """

    markup = InlineKeyboardMarkup(
        keyboard=[
            [
                InlineKeyboardButton(text='День', callback_data='history_day'),
                InlineKeyboardButton(text='Неделя', callback_data='history_week'),
                InlineKeyboardButton(text='Месяц', callback_data='history_month')
            ],
            [
                InlineKeyboardButton(text='Вся история', callback_data='history_all')
            ]
        ]
    )

    bot.send_message(message.chat.id, 'Выберите период, за которую надо выводить историю:', reply_markup=markup)


def get_history(bot: TeleBot, call: CallbackQuery) -> None:
    """
    Функция вывода истории из БД по заданному периоду

    Args:
        bot (TeleBot): Принимает объект TeleBot
        call (CallbackQuery): Принимает объект-CallbackQuery от Telegram
    """

    # TODO придумать вывод порциями и дописать функцию
    if call.data == "history_day":
        bot.answer_callback_query(call.id, "Выбран период: День", show_alert=True)
        histories = bot_db.get_history(user_id=call.from_user.id, within='day')
        for record in histories:
            output_text = ("""
Дата: <b>{dt}</b>
Команда: <b>{cmd}</b>
Сообщение: <b>{ms}</b>
Запрос: <b>{req}</b>
    """).format(
                dt=record[0],
                cmd=record[1],
                ms=record[2],
                req=record[3]
            )
            bot.send_message(chat_id=call.message.chat.id, text=output_text, parse_mode='html')
    elif call.data == "history_week":
        bot.answer_callback_query(call.id, "Выбран период: Неделя", show_alert=True)
    elif call.data == "history_month":
        bot.answer_callback_query(call.id, "Выбран период: Месяц", show_alert=True)
    elif call.data == "history_all":
        bot.answer_callback_query(call.id, "Выбран период: Вся история", show_alert=True)

    # Удаляем клавиатуру
    bot.edit_message_text('Принято!',
                          chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          reply_markup=None
                          )

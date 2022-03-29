"""
Главный скрипт бота besthoteloffers_bot.py
Содержит основную логику работы бота.
"""
# import re
from datetime import date

import telebot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot_db_pw import *
# from commands import history
from commands.calendar import MyStyleCalendar, STEPS
from config import BOT_TOKEN
from settings import emoji

logger.add('Log/debug.log', encoding='utf-8')

# Подключение к Telegram Bot API
bot = telebot.TeleBot(BOT_TOKEN)

# Проверка корректного подключения к Telegram Bot API
bot_info = bot.get_me()
logger.info((f"""
    ID бота: {bot_info.id}, 
    Название бота: {bot_info.first_name}, 
    Пользователь: {bot_info.username}, 
    Подключение: {bot_info.is_bot}"""))

# Инициализируем БД
init_db()


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

Меня ещё разрабатывают, но я уже кое-что умею.
Давай попробуем найти:
/lowprice - топ самых дешёвых отелей
/highprice - топ самых дорогих отелей""")

    send_message_next_starts = (f"""
<b>С возвращением  {message.from_user.first_name} {message.from_user.last_name}!</b>

Похоже, ты решил начать заново?
Что ж, давай начнём. Выбери команду:
/lowprice - топ самых дешёвых отелей
/highprice - топ самых дорогих отелей""")

    if not user_exists(user_id=message.from_user.id):
        # Добавляем пользователя в БД
        with db:
            User(
                user_id=message.from_user.id,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                date=convert_data(value=message.date)
            ).save(force_insert=True)

        # Отправляем первое стартовое сообщение
        bot.send_message(chat_id=message.chat.id, text=send_message_first_start, parse_mode='html')
    else:
        # Отправляем второе стартовое сообщение
        bot.send_message(chat_id=message.chat.id, text=send_message_next_starts, parse_mode='html')

    # Добавляем команду в БД
    with db:
        History(
            user_id=message.from_user.id,
            commands=message.text,
            date=convert_data(value=message.date)
        ).save(force_insert=True)


@bot.message_handler(commands=['help'])
@logger.catch
def command_help(message: Message) -> None:
    bot.send_message(message.chat.id, 'Извини, но данная команда пока в разработке.')
    # TODO дописать функцию


@bot.message_handler(commands=['reset'])
@logger.catch
def command_reset(message: Message) -> None:
    bot.send_message(message.chat.id, 'Извини, но данная команда пока в разработке.')
    # TODO дописать функцию


@bot.message_handler(commands=['settings'])
@logger.catch
def command_settings(message: Message) -> None:
    bot.send_message(message.chat.id, 'Извини, но данная команда пока в разработке.')
    # TODO дописать функцию


@bot.message_handler(commands=['lowprice', 'highprice', 'bestdeal', 'history'])
@logger.catch
def search_commands(message: Message) -> None:
    """
    Функция-обработчик команд /lowprice, /highprice, /bestdeal, /history

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    # Добавляем сообщение в БД
    with db:
        History(
            user_id=message.from_user.id,
            messages=message.text,
            date=convert_data(value=message.date)
        ).save(force_insert=True)

    # Согласно команде вызываем соответствующий модуль
    match message.text:
        case '/lowprice' | '/highprice':
            set_searching_function(
                user_id=message.from_user.id,
                user_searching_function=re.search(r'\w+', message.text).group()
            )
            bot.send_message(chat_id=message.chat.id, text='Куда Вы едете?')
            bot.register_next_step_handler(message=message, callback=search_city)
        case '/bestdeal':
            # TODO дописать функцию и удалить заглушку
            bot.send_message(message.chat.id, 'Извини, но данная команда пока в разработке.')
        case '/history':
            # TODO дописать функцию и удалить заглушку
            # history.req_period(bot=bot, message=message)
            bot.send_message(message.chat.id, 'Извини, но данная команда пока в разработке.')


@logger.catch
def search_city(message: Message) -> None:
    """
    Функция поиска города.
    Выполняет поиск введённого пользователем города и выводит InLine
    клавиатуру с вариантами найденных городов.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    temp = bot.send_message(chat_id=message.chat.id, text='Выполняю поиск...', parse_mode='HTML')
    cities = get_cities(message=message)
    keyboard = InlineKeyboardMarkup()

    if not cities:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=temp.id,
            text='По вашему запросу ничего не найдено...\n/help',
            parse_mode='HTML'
        )
    else:
        for city_name, city_id in cities.items():
            keyboard.add(InlineKeyboardButton(text=city_name, callback_data=city_id))
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=temp.id,
            text='Предлагаю немного уточнить запрос:',
            reply_markup=keyboard
        )


@bot.callback_query_handler(func=lambda call: call.message.text == 'Предлагаю немного уточнить запрос:')
@logger.catch
def city_handler(call: CallbackQuery) -> None:
    """
    Функция-обработчик нажатия на кнопку нужного города
    и переход к следующему действию по сценарию.

    Args:
        call (CallbackQuery): Принимает объект-CallbackQuery от Telegram
    """

    set_city_id(user_id=call.message.chat.id, user_city=call.data)
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)

    if get_advanced_question_flag(user_id=call.message.chat.id):
        pass  # TODO Дописать функцию выбора диапазона цен
    else:
        ask_for_date_in(call.message)


@logger.catch
def ask_for_date_in(message: Message) -> None:
    """
    Функция создаёт календарь для даты заезда в отель и запрашивает год даты.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    # Сбрасываем даты заезда и выезда в БД
    User(id=User.get_pk_id(message.chat.id), date_in=None, date_out=None).save()

    # Создаём и выводим календарь для выбора года заезда
    calendar, step = MyStyleCalendar(calendar_id=1, locale='ru', min_date=date.today()).build()
    bot.send_message(chat_id=message.chat.id, text=f'Выберите {STEPS[step]} заезда', reply_markup=calendar)


@logger.catch
def ask_for_date_out(message: Message) -> None:
    """
    Функция создаёт календарь для даты выезда из отеля и запрашивает год даты.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    # Создаём и выводим календарь для выбора года выезда
    calendar, step = MyStyleCalendar(calendar_id=2, locale='ru',
                                     min_date=User.get(User.user_id == message.chat.id).date_in
                                     ).build()

    bot.send_message(chat_id=message.chat.id, text=f'Выберите {STEPS[step]} выезда', reply_markup=calendar)


@bot.callback_query_handler(func=MyStyleCalendar.func(calendar_id=1))
@logger.catch
def set_date_in(call: CallbackQuery) -> None:
    """
    Функция - обработчик нажатий на кнопки календаря.
    Запрашивает месяц и день даты заезда, записывает дату заезда в БД
    и вызывает функцию создания календаря для даты выезда из отеля.

    Args:
        call (CallbackQuery): Принимает объект-CallbackQuery от Telegram
    """

    # Выводим календарь для выбора месяца и дня заезда
    result, key, step = MyStyleCalendar(calendar_id=1,
                                        locale='ru',
                                        min_date=date.today()
                                        ).process(call_data=call.data)
    if not result and key:
        bot.edit_message_text(text=f'Выберите {STEPS[step]} заезда',
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              reply_markup=key)
    elif result:
        bot.edit_message_text(text=f'Выбрана дата заезда:  {result}',
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id
                              )

        # Записываем дату заезда в БД и запрашиваем год выезда
        User(id=User.get_pk_id(call.from_user.id), date_in=result).save()
        ask_for_date_out(call.message)


@bot.callback_query_handler(func=MyStyleCalendar.func(calendar_id=2))
@logger.catch
def set_date_out(call: CallbackQuery) -> None:
    """
    Функция - обработчик нажатий на кнопки календаря.
    Запрашивает месяц и день даты выезда, записывает дату выезда в БД
    и вызывает функцию запроса кол-ва отелей.

    Args:
        call (CallbackQuery): Принимает объект-CallbackQuery от Telegram
    """

    # Выводим календарь для выбора месяца и дня выезда
    result, key, step = MyStyleCalendar(calendar_id=2,
                                        locale='ru',
                                        min_date=User.get(User.user_id == call.from_user.id).date_in
                                        ).process(call_data=call.data)
    if not result and key:
        bot.edit_message_text(text=f'Выберите {STEPS[step]} выезда',
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              reply_markup=key)
    elif result:
        bot.edit_message_text(text=f'Выбрана дата выезда:  {result}',
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id
                              )

        # Записываем дату выезда в БД и запрашиваем кол-во отелей
        User(id=User.get_pk_id(call.from_user.id), date_out=result).save()
        ask_for_hotels_count(call.message)


@logger.catch
def ask_for_hotels_count(message: Message) -> None:
    """
    Функция запрашивает кол-во отелей и переходит к следующему действию по сценарию.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    bot.send_message(chat_id=message.chat.id, text='Сколько отелей вывести? (не более 10)')
    bot.register_next_step_handler(message=message, callback=photo_needed)


@logger.catch
def photo_needed(message: Message) -> None:
    """
    Функция запрашивает необходимость вывода фотографий отелей в виде InLine клавиатуры.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    set_hotels_count(user_id=message.chat.id, user_hotels_count=abs(int(message.text)))
    keyboard = InlineKeyboardMarkup()
    [keyboard.add(InlineKeyboardButton(x, callback_data=x)) for x in ['Да', 'Нет']]
    bot.send_message(chat_id=message.chat.id, text='Интересуют фотографии объектов?', reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.message.text == 'Интересуют фотографии объектов?')
@logger.catch
def set_photo_needed(call: CallbackQuery) -> None:
    """
    Функция обрабатывает ответ пользователя о необходимости вывода
    фотографий отелей и в зависимости от этого выбирает следующее
    действию по сценарию.

    Args:
        call (CallbackQuery): Принимает объект-CallbackQuery от Telegram
    """

    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
    if call.data == 'Да':
        set_needed_photo(user_id=call.message.chat.id, user_needed_photo=True)
        numbers_of_photo(call.message)
    else:
        set_needed_photo(user_id=call.message.chat.id, user_needed_photo=False)
        resulting_function(call.message)


@logger.catch
def numbers_of_photo(message: Message) -> None:
    """
    Функция запрашивает кол-во фотографий отелей
    и переходит к следующему действию по сценарию.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    bot.send_message(chat_id=message.chat.id, text='Сколько фотографий выводить по каждому отелю?')
    bot.register_next_step_handler(message=message, callback=resulting_function)


@logger.catch
def resulting_function(messages: Message) -> None:
    """
    Результирующая функция, которая:
    1) обрабатывает кол-во фотографий отелей (если пользователь выбрал
        необходимость вывода фотографий),
    2) выполняет поиск отелей,
    3) формирует и отправляет результат пользователю в Telegram.

    Args:
        messages (Message): Принимает объект-сообщение от Telegram
    """

    if get_needed_photo(user_id=messages.chat.id):
        set_photos_count(user_id=messages.chat.id, user_photos_count=abs(int(messages.text)))

    temp = bot.send_message(chat_id=messages.chat.id, text='Выполняю поиск...')
    total_days = (User.get(User.user_id == messages.chat.id).date_out -
                  User.get(User.user_id == messages.chat.id).date_in)
    hotels_glossary, search_link = get_hotels(user_id=messages.chat.id)

    if hotels_glossary:
        bot.edit_message_text(chat_id=messages.chat.id,
                              message_id=temp.id, text='Я нашёл для тебя следующие варианты...')
        for index, hotels in enumerate(hotels_glossary.values()):
            if index + 1 > get_hotels_count(user_id=messages.chat.id):
                break
            cost, curr_value = hotels['price'].replace(',', '').split()
            output_text = ("""
\n\n{e_hotel}{name}{e_hotel}
\n\n{e_address}<a href='{address_link}'>{address}</a>
\n\n{e_dist}Ближайшие ориентиры: {distance}
\n\n{e_price}Цена за ночь: {price}
\n{e_total}Общая сумма за {total_days} дней:  {total_price} {curr_value}
\n\n{e_link}<a href='{link}'>Подробнее на hotels.com</a>""".format(
                name=hotels['name'],
                address=get_address(hotels=hotels),
                distance=get_landmarks(hotels=hotels),
                price=hotels['price'].replace(',', ''),
                total_days=total_days.days,
                total_price=int(cost) * total_days.days,
                curr_value=curr_value,
                e_hotel=emoji['hotel'],
                e_address=emoji['address'],
                e_dist=emoji['landmarks'],
                e_price=emoji['price'],
                e_total=emoji['total_price'],
                e_link=emoji['link'],
                link='https://hotels.com/ho' + str(hotels['id']),
                address_link='https://google.com/maps/place/' + hotels['coordinate']
                )
            )

            if get_needed_photo(user_id=messages.chat.id):
                photos = get_photos(user_id=messages.chat.id, hotel_id=int(hotels['id']), text=output_text)
                for size in ['z', 'y', 'd', 'n', '_']:
                    try:
                        bot.send_media_group(chat_id=messages.chat.id, media=photos)
                        break
                    except telebot.apihelper.ApiTelegramException:
                        photos = [InputMediaPhoto(caption=obj.caption,
                                                  media=obj.media[:-5] + f'{size}.jpg',
                                                  parse_mode=obj.parse_mode)
                                  for obj in photos]
            else:
                bot.send_message(chat_id=messages.chat.id,
                                 text=output_text,
                                 parse_mode='HTML',
                                 disable_web_page_preview=True
                                 )
        bot.send_message(chat_id=messages.chat.id,
                         text=("""
Не нашли подходящий вариант?\nЕщё больше отелей по вашему запросу\\: [смотреть]({link})
\nХотите продолжить работу с ботом? /help""").format(link=search_link),
                         parse_mode='MarkdownV2',
                         disable_web_page_preview=True
                         )
    else:
        bot.edit_message_text(chat_id=messages.chat.id,
                              message_id=temp.id,
                              text='По вашему запросу ничего не найдено...\n/help')


@bot.message_handler(content_types=['text'])
@logger.catch
def get_text_messages(message: Message) -> None:
    """
    Функция get_text_message, выполняет различные действия в зависимости
    от сообщения пользователя.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """
    # Добавляем сообщение в БД
    with db:
        History(
            user_id=message.from_user.id,
            messages=message.text,
            date=convert_data(value=message.date)
        ).save(force_insert=True)

    # Обрабатываем введённый текст
    if message.text.lower() == 'привет':
        bot.send_message(message.chat.id, 'Привет! 👋\nПока я умею столько. Но меня продолжают кодить. 😉')
    else:
        bot.send_message(message.chat.id, 'Я тебя не понял. 🤷\nПовтори, пожалуйста.')


# @bot.callback_query_handler(func=lambda call: True)
# @logger.catch
# def callback_query(call: CallbackQuery) -> None:
#     """
#     Функция-обработчик нажатий на кнопки клавиатуры
#
#     Args:
#         call (CallbackQuery): Принимает объект-CallbackQuery от Telegram
#     """
#     match call.data:
#         case 'history_day' | 'history_week' | 'history_month' | 'history_all':
#             history.get_history(bot=bot, call=call)


logger.info('Бот в работе')
bot.infinity_polling()

"""
Главный скрипт бота besthoteloffers_bot.py
Содержит основную логику работы бота.
"""

from datetime import date

import telebot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot_db_pw import *
from commands.calendar import MyStyleCalendar, STEPS
from config import BOT_TOKEN
from settings import emoji, star_rating, night_declension

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
    Функция-обработчик команды /start.
    Выводит приветственное сообщение, затем вызывает команду /help.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    send_message_first_start = (f"""
<b>Приветствую  {message.from_user.first_name} {message.from_user.last_name}!

Я - Best Hotel Offers Bot.</b>
Я умею находить и выводить лучшие отели мира, в любом городе, по твоим запросам.
А ещё я запоминаю все отели, которые ты искал, и при необходимости могу их вывести.

Итак, давай начнём.""")

    send_message_next_starts = (f"""
<b>С возвращением  {message.from_user.first_name} {message.from_user.last_name}!</b>

Похоже, ты решил начать заново?
Что ж, давай начнём.""")

    logger.info('Пользователь: {user_id}  | Команда: "/start"'.format(user_id=message.from_user.id))

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
        bot.send_message(chat_id=message.chat.id, text=send_message_first_start, parse_mode='HTML')
    else:
        # Отправляем второе стартовое сообщение
        bot.send_message(chat_id=message.chat.id, text=send_message_next_starts, parse_mode='HTML')

    command_help(message=message)


@bot.message_handler(commands=['help'])
@logger.catch
def command_help(message: Message) -> None:
    """
    Функция-обработчик команды /help.
    Выводит команды и краткую справку по ним.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    help_text = ("""
Выбери команду:

/lowprice - топ самых дешёвых отелей
/highprice - топ самых дорогих отелей
/bestdeal - лучшие отели по твоим запросам

/history - вывод истории поиска отелей
/reset - сброс параметров и удаление истории поиска""")

    logger.info('Пользователь: {user_id}  | Команда: "/help"'.format(user_id=message.from_user.id))

    bot.send_message(chat_id=message.chat.id, text=help_text, parse_mode='HTML')


@bot.message_handler(commands=['reset'])
@logger.catch
def command_reset(message: Message) -> None:
    """
    Функция-обработчик команды /reset.
    Сбрасывает все параметры пользователя и удаляет историю его команд.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    logger.info('Пользователь: {user_id}  | Команда: "/reset"'.format(user_id=message.from_user.id))

    History.delete_history_data(user_id=message.from_user.id)
    User.reset_to_default_search_data(user_id=message.from_user.id)

    bot.send_message(chat_id=message.chat.id,
                     text='Все параметры сброшены!\nИстория команд удалена!\n\nХочешь продолжить? /help',
                     parse_mode='HTML',
                     disable_web_page_preview=True
                     )


@bot.message_handler(commands=['settings'])
@logger.catch
def command_settings(message: Message) -> None:
    logger.info('Пользователь: {user_id}  | Команда: "/settings"'.format(user_id=message.from_user.id))
    bot.send_message(message.chat.id, 'Извини, но данная команда пока в разработке.')
    # TODO дописать функцию


@bot.message_handler(commands=['lowprice', 'highprice', 'bestdeal', 'history'])
@logger.catch
def search_commands(message: Message) -> None:
    """
    Функция-обработчик команд /lowprice, /highprice, /bestdeal, /history.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    logger.info('Пользователь: {user_id}  | Команда: "{cmd}"'.format(user_id=message.from_user.id,
                                                                     cmd=message.text))

    match message.text:
        case '/lowprice' | '/highprice' | '/bestdeal':
            User.reset_to_default_search_data(user_id=message.from_user.id)
            set_searching_function(
                user_id=message.from_user.id,
                user_searching_function=re.search(r'\w+', message.text).group()
            )
            bot.send_message(chat_id=message.chat.id, text='В какой город планируем выезд?')
            bot.register_next_step_handler(message=message, callback=search_city)

        case '/history':
            markup = InlineKeyboardMarkup(keyboard=[
                [InlineKeyboardButton(text='Последний поиск', callback_data='history_last')],
                [InlineKeyboardButton(text='За последний день', callback_data='history_day')],
                [InlineKeyboardButton(text='За последнюю неделю', callback_data='history_week')]
                ])

            bot.send_message(message.chat.id, 'Какую историю выводить?', reply_markup=markup)


@logger.catch
def search_city(message: Message) -> None:
    """
    Функция поиска города.
    Выполняет поиск введённого пользователем города и выводит InLine
    клавиатуру с вариантами найденных городов.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    logger.info('Пользователь: {user_id}  | Сообщение: "{msg}"'.format(user_id=message.chat.id,
                                                                       msg=message.text))

    temp = bot.send_message(chat_id=message.chat.id, text='Выполняю поиск...', parse_mode='HTML')
    cities = get_cities(message=message)
    keyboard = InlineKeyboardMarkup()

    if not cities:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=temp.id,
            text=("""
К сожалению, я ничего подходящего не нашёл {sad}...
(Российские города всё ещё недоступны)

Может попробуешь ещё раз?  /help""").format(sad=emoji['sadness']),
            parse_mode='HTML'
        )
    else:
        for city_name, city_id in cities.items():
            keyboard.add(InlineKeyboardButton(text=city_name, callback_data=city_id))
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=temp.id,
            text='Куда именно из этих:',
            reply_markup=keyboard
        )


@bot.callback_query_handler(func=lambda call: call.message.text == 'Куда именно из этих:')
@logger.catch
def city_handler(call: CallbackQuery) -> None:
    """
    Функция-обработчик нажатия на кнопку нужного города
    и переход к следующему действию по сценарию.

    Args:
        call (CallbackQuery): Принимает объект-CallbackQuery от Telegram
    """

    logger.info('Пользователь: {user_id}  | Кнопка: "{btn}"'.format(user_id=call.message.chat.id,
                                                                    btn=call.data))

    set_city_id(user_id=call.message.chat.id, user_city=call.data)
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)

    if get_advanced_question_flag(user_id=call.message.chat.id):
        ask_for_price_range(call.message)
    else:
        ask_for_date_in(call.message)


@logger.catch
def ask_for_price_range(message: Message) -> None:
    """
    Функция запрашивает диапазон цен у пользователя

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    bot.send_message(chat_id=message.chat.id,
                     text="""
Сколько денег у тебя в кармане? Шучу {smile}.

Укажи диапазон стоимости номера за ночь в ({cur}):
(Например: "от 1000 до 50000", "1000-50000", "1000 50000")""".format(cur=get_currency(user_id=message.chat.id),
                                                                     smile=emoji['smile']),
                     parse_mode='HTML')

    bot.register_next_step_handler(message=message, callback=ask_for_distance_range)


@logger.catch
def ask_for_distance_range(message: Message) -> None:
    """
    Функция обрабатывает введённый пользователем диапазон цен и
    запрашивает максимальное расстояние, на котором находится отель от центра.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    logger.info('Пользователь: {user_id}  | Сообщение: "{msg}"'.format(user_id=message.chat.id,
                                                                       msg=message.text))

    price_range = list(set(map(int, map(lambda string: string.replace(',', '.'),
                                        re.findall(r'\d+[.,\d+]?\d?', message.text)))))
    if len(price_range) != 2:
        bot.send_message(chat_id=message.chat.id, text='Ошибка диапазона!\nМожет попробуешь заново?  /help')
        raise ValueError('Ошибка диапазона!')
    else:
        set_price_range(user_id=message.chat.id, price_range=price_range)
        bot.send_message(chat_id=message.chat.id,
                         text="""
Как далеко (в км) от центра должен находится отель?:
(Например: "от 1 до 3", "1-3", "1 3")""",
                         parse_mode='HTML')

        bot.register_next_step_handler(message=message, callback=ask_for_date_in)


@logger.catch
def ask_for_date_in(message: Message) -> None:
    """
    Функция обрабатывает введённое пользователем расстояние до центра,
    создаёт календарь для даты заезда в отель и запрашивает год даты.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    if get_advanced_question_flag(user_id=message.chat.id):
        logger.info('Пользователь: {user_id}  | Сообщение: "{msg}"'.format(user_id=message.chat.id,
                                                                           msg=message.text))

        distance_range = list(set(map(float, map(lambda string: string.replace(',', '.'),
                                                 re.findall(r'\d+[.,\d+]?\d?', message.text)))))
        if len(distance_range) != 2:
            bot.send_message(chat_id=message.chat.id, text='Ошибка расстояния!\nМожет попробуешь заново?  /help')
            raise ValueError('Ошибка расстояния!')
        else:
            set_distance_range(user_id=message.chat.id, dist_range=distance_range)

    # Сбрасываем даты заезда и выезда в БД
    with db:
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
    with db:
        min_date = User.get(User.user_id == message.chat.id).date_in

    calendar, step = MyStyleCalendar(calendar_id=2, locale='ru', min_date=min_date).build()

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
        logger.info('Пользователь: {user_id}  | Дата заезда: "{date}"'.format(user_id=call.message.chat.id,
                                                                              date=result))
        bot.edit_message_text(text=f'Выбрана дата заезда:  {result}',
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id
                              )

        # Записываем дату заезда в БД и запрашиваем год выезда
        with db:
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
    with db:
        min_date = User.get(User.user_id == call.from_user.id).date_in

    result, key, step = MyStyleCalendar(calendar_id=2, locale='ru', min_date=min_date).process(call_data=call.data)

    if not result and key:
        bot.edit_message_text(text=f'Выберите {STEPS[step]} выезда',
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              reply_markup=key)
    elif result:
        logger.info('Пользователь: {user_id}  | Дата выезда: "{date}"'.format(user_id=call.message.chat.id,
                                                                              date=result))
        bot.edit_message_text(text=f'Выбрана дата выезда:  {result}',
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id
                              )

        # Записываем дату выезда в БД и запрашиваем кол-во отелей
        with db:
            User(id=User.get_pk_id(call.from_user.id), date_out=result).save()

        ask_for_hotels_count(call.message)


@logger.catch
def ask_for_hotels_count(message: Message) -> None:
    """
    Функция запрашивает кол-во отелей и переходит к следующему действию по сценарию.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    bot.send_message(chat_id=message.chat.id, text='Сколько отелей вывести?\n(в цифрах, но не более 10)')
    bot.register_next_step_handler(message=message, callback=photo_needed)


@logger.catch
def photo_needed(message: Message) -> None:
    """
    Функция запрашивает необходимость вывода фотографий отелей в виде InLine клавиатуры.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    logger.info('Пользователь: {user_id}  | Сообщение: "{msg}"'.format(user_id=message.chat.id,
                                                                       msg=message.text))

    if not message.text.isalpha():
        user_hotels_count = abs(int(re.search(r'\d+', message.text).group()))
        if user_hotels_count > 10:
            bot.send_message(chat_id=message.chat.id, text='Ошибка! Кол-во больше 10!\nМожет попробуешь заново?  /help')
            raise ValueError('Ошибка! Пользователь ввёл цифру больше 10.')
        else:
            set_hotels_count(user_id=message.chat.id, user_hotels_count=user_hotels_count)
    else:
        bot.send_message(chat_id=message.chat.id, text='Ошибка! Не вижу цифр!\nМожет попробуешь заново?  /help')
        raise ValueError('Ошибка кол-ва отелей! Пользователь не ввёл цифры.')

    keyboard = InlineKeyboardMarkup()
    [keyboard.add(InlineKeyboardButton(x, callback_data=x)) for x in ['Да', 'Нет']]

    bot.send_message(chat_id=message.chat.id, text='Фотографии отелей нужны?', reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.message.text == 'Фотографии отелей нужны?')
@logger.catch
def set_photo_needed(call: CallbackQuery) -> None:
    """
    Функция обрабатывает ответ пользователя о необходимости вывода
    фотографий отелей и в зависимости от этого выбирает следующее
    действию по сценарию.

    Args:
        call (CallbackQuery): Принимает объект-CallbackQuery от Telegram
    """

    logger.info('Пользователь: {user_id}  | Кнопка: "{btn}"'.format(user_id=call.message.chat.id,
                                                                    btn=call.data))

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
def resulting_function(message: Message) -> None:
    """
    Результирующая функция, которая:
    1) обрабатывает кол-во фотографий отелей (если пользователь выбрал
        необходимость вывода фотографий),
    2) выполняет поиск отелей,
    3) формирует и отправляет результат пользователю в Telegram.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
    """

    if get_needed_photo(user_id=message.chat.id):
        logger.info('Пользователь: {user_id}  | Сообщение: "{msg}"'.format(user_id=message.chat.id,
                                                                           msg=message.text))
        if not message.text.isalpha():
            set_photos_count(user_id=message.chat.id,
                             user_photos_count=abs(int(re.search(r'\d+', message.text).group())))
        else:
            bot.send_message(chat_id=message.chat.id, text='Ошибка! Не вижу цифр!\nМожет попробуешь заново?  /help')
            raise ValueError('Ошибка кол-ва фото! Пользователь не ввёл цифры.')

    temp = bot.send_message(chat_id=message.chat.id, text='Выполняю поиск...')

    with db:
        date_in = User.get(User.user_id == message.chat.id).date_out
        date_out = User.get(User.user_id == message.chat.id).date_in

    total_days = date_out - date_in
    hotels_glossary, search_link = get_hotels(user_id=message.chat.id)

    if hotels_glossary:
        bot.edit_message_text(chat_id=message.chat.id,
                              message_id=temp.id, text='УРА!!!\nКажется, я кое-что нашёл для тебя. Вывожу...')
        for index, hotels in enumerate(hotels_glossary.values()):
            if index + 1 > get_hotels_count(user_id=message.chat.id):
                break
            cost, curr_value = hotels['price'].replace(',', '').split()
            output_text = ("""
\n\n{e_hotel} <b>{name} </b>
\n{e_star} Категория отеля:  <b>{stars}</b>
\n\n{e_address} <a href='{address_link}'>{address}</a>
\n\n{e_dist} Ближайшие ориентиры: <b>{distance}</b>
\n\n{e_price} Цена за ночь:  <b>{price}</b>
\n{e_total} Общая сумма за <b>{total_days}</b> {night}:  <b>{total_price} {curr_value}</b>
\n\n{e_link} <a href='{link}'>Подробнее на hotels.com</a>""".format(
                name=hotels['name'],
                stars=star_rating(rating=hotels['stars']),
                address=get_address(hotels=hotels),
                distance=get_landmarks(hotels=hotels),
                price=hotels['price'].replace(',', ''),
                total_days=abs(total_days.days),
                night=night_declension(days=abs(total_days.days)),
                total_price=int(cost) * abs(total_days.days),
                curr_value=curr_value,
                e_hotel=emoji['hotel'],
                e_star=emoji['star'],
                e_address=emoji['address'],
                e_dist=emoji['landmarks'],
                e_price=emoji['price'],
                e_total=emoji['total_price'],
                e_link=emoji['link'],
                link='https://hotels.com/ho' + str(hotels['id']),
                address_link='https://google.com/maps/place/' + hotels['coordinate']
                )
            )

            if get_needed_photo(user_id=message.chat.id):
                photos = get_photos(user_id=message.chat.id, hotel_id=int(hotels['id']), text=output_text)
                for size in ['z', 'y', 'd', 'n', '_']:
                    try:
                        bot.send_media_group(chat_id=message.chat.id, media=photos)
                        break
                    except telebot.apihelper.ApiTelegramException:
                        photos = [InputMediaPhoto(caption=obj.caption,
                                                  media=obj.media[:-5] + f'{size}.jpg',
                                                  parse_mode=obj.parse_mode)
                                  for obj in photos]
            else:
                bot.send_message(chat_id=message.chat.id,
                                 text=output_text,
                                 parse_mode='HTML',
                                 disable_web_page_preview=True
                                 )
        bot.send_message(chat_id=message.chat.id,
                         text=("""
Не подошли эти варианты?  Почемууу? {ask}

Ладно, шучу\\. {smile}
Ещё больше отелей по твоему запросу [смотри здесь]({link})

Хочешь заново?  /help""").format(ask=emoji['ask'],
                                 smile=emoji['smile'],
                                 link=search_link),
                         parse_mode='MarkdownV2',
                         disable_web_page_preview=True
                         )
    else:
        bot.edit_message_text(chat_id=message.chat.id,
                              message_id=temp.id,
                              text=("""
К сожалению, я ничего подходящего не нашёл {sad}...
Может попробуешь заново?  /help""").format(sad=emoji['sadness']),
                              parse_mode='HTML'
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

    logger.info('Пользователь: {user_id}  | Сообщение: "{msg}"'.format(user_id=message.chat.id,
                                                                       msg=message.text))

    if message.text.lower() == 'привет':
        bot.send_message(chat_id=message.chat.id, text='Привет! 👋\nНужна помощь?  /help')
    else:
        bot.send_message(chat_id=message.chat.id,
                         text="""
Я тебя не понял. 🤷
Может попробуешь заново?  /help
Или введи команду\\."""
                         )


@bot.callback_query_handler(func=lambda call: call.message.text == 'Какую историю выводить?')
@logger.catch
def create_history(call: CallbackQuery) -> None:
    """
    Функция обрабатывает ответ пользователя о выводе истории
    и вызывает функцию показа истории с соответствующими параметрами.

    Args:
        call (CallbackQuery): Принимает объект-CallbackQuery от Telegram
    """

    logger.info('Пользователь: {user_id}  | Кнопка: "{btn}"'.format(user_id=call.message.chat.id,
                                                                    btn=call.data))

    match call.data:
        case 'history_last':
            show_history(message=call.message, text='Последний поиск:', within='last')
        case 'history_day':
            show_history(message=call.message, text='История за последний день:', within='day')
        case 'history_week':
            show_history(message=call.message, text='История за последнюю неделю:', within='week')


@logger.catch
def show_history(message: Message, text: str, within: str) -> None:
    """
    Функция вывода истории пользователю.

    Args:
        message (Message): Принимает объект-сообщение от Telegram
        text (str): Принимает текст, соответствующий выбору пользователя
        within (str): Принимает значения last(последний), day(день), week(неделя),
                        за которые нужно выводить историю
    """

    bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text=text)

    # Получаем историю из БД
    histories = get_history(user_id=message.chat.id, within=within)

    # Выводим историю
    if histories:
        for record in histories:
            output_text = ("""
Дата:  <b>{dt}</b>
Команда:  <b>{cmd}</b>
Город:  <b>{req}</b>

Найденные отели:
<b>{ans}</b>""").format(dt=record['date'],
                        cmd=record['commands'],
                        req=record['requests'],
                        ans='\n'.join(json.loads(record['answers']))
                        )

            bot.send_message(chat_id=message.chat.id, text=output_text,
                             parse_mode='HTML', disable_web_page_preview=True)
        else:
            bot.send_message(chat_id=message.chat.id,
                             text='Хочешь продолжить?  /help',
                             parse_mode='HTML',
                             disable_web_page_preview=True
                             )
    else:
        bot.send_message(chat_id=message.chat.id,
                         text='Поисков пока не было.\n\nХочешь продолжить?  /help')


logger.info('Бот в работе')
bot.infinity_polling()

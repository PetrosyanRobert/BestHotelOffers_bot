"""
Модуль для работы с БД.
Содержит функции для чтения из БД и записи данных в БД.
"""

import argparse
from datetime import datetime
from typing import Any

from loguru import logger
from playhouse.sqlite_ext import *
from telebot.types import Message, InputMediaPhoto

from commands import recurring, hilowprice
from config import DATABASE


# Подключаемся к БД
db = SqliteExtDatabase(DATABASE)


searching_functions = {
    'lowprice': hilowprice.lowprice,
    'highprice': hilowprice.highprice
}


class DateTimeField(Field):
    """
    Сабкласс класса DateTimeField модуля peewee,
    наследуется от класса Field.

    Необходим для переопределения метода db_value так, чтобы значения
    времени в формате timestamp конвертировались в стандартный формат
    YYYY-MM-DD HH:MM:SS перед записью в БД.
    """

    def db_value(self, value: Any) -> Any:
        """
        Переопределение метода db_value у поля DateTimeField

        Args:
            value (Any): Принимает значение даты и времени в произвольном формате

        Returns (Any): Конвертированное либо нет значение даты и времени
        """

        if isinstance(value, int):
            date_value = datetime.fromtimestamp(value)
            result = date_value.strftime('%Y-%m-%d %H:%M:%S')
        else:
            result = value
        return result


class ModelBase(Model):
    """
    Класс ModelBase, наследуется от класса Model библиотеки peewee.
    Дочерние классы: User и History.

    Данный класс содержит одинаковые поля таблиц и ссылку на БД
    для дочерних классов.
    """

    id = AutoField(primary_key=True)

    class Meta:
        database = db


class User(ModelBase):
    user_id = IntegerField(unique=True)
    first_name = CharField(max_length=64, null=True)
    last_name = CharField(max_length=64, null=True)
    join_date = DateTimeField(default=datetime.now())
    cities = JSONField(null=True, default=None)
    city_id = IntegerField(null=True, default=None)
    city_name = CharField(max_length=50, null=True, default=None)
    hotels_count = IntegerField(null=True, default=None)
    needed_photo = BooleanField(null=True, default=None)
    photos_count = IntegerField(null=True, default=None)
    price_range = CharField(max_length=30, null=True, default=None)
    dist_range = CharField(max_length=10, null=True, default=None)
    language = CharField(max_length=8, null=True, default='ru_RU')
    lang_flag = BooleanField(null=True, default=False)
    currency = CharField(max_length=6, null=True, default='RUB')
    cur_flag = BooleanField(null=True, default=False)
    advanced_question_flag = BooleanField(null=True, default=False)
    searching_function = CharField(max_length=22, null=True, default=None)

    class Meta:
        table_name = 'users'

    @classmethod
    def get_pk_id(cls, user_id: int) -> int:
        """
        Геттер для получения id первичного ключа из БД по id пользователя.

        Args:
            user_id (int): Принимает id пользователя из его команды или сообщения

        Returns (int): id первичного ключа из БД
        """

        pk_id = cls.get(cls.user_id == user_id).id

        return pk_id


class History(ModelBase):
    date = DateTimeField(default=datetime.now())
    user_id = ForeignKeyField(model=User, field='user_id')
    commands = CharField(max_length=15, null=True)
    messages = CharField(max_length=50, null=True)
    requests = TextField(null=True)
    answers = TextField(null=True)

    class Meta:
        table_name = 'user_messages'


@logger.catch
def init_db(force: bool = False) -> None:
    """
    Функция, которая инициализирует БД.
    Проверяет наличие нужных таблиц, если их нет, то создаёт.
    При вызове с аргументом force=True удаляет таблицы, перед тем,
    как создать их.

    Args:
        force (bool): Если данный аргумент True, то все таблицы удаляются
                        (по умолчанию: False)
    """

    with db:
        # Удаление всех таблиц, если аргумент force = True
        if force:
            db.drop_tables([User, History])

        # Создание таблиц
        db.create_tables([User, History])

    logger.info('БД инициализирована')


@logger.catch
def user_exists(user_id: int) -> bool:
    """
    Функция, которая проверяет есть ли пользователь в БД.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (bool): Возвращает True, если пользователь уже есть в БД, иначе - False
    """

    with db:
        try:
            User.get(User.user_id == user_id)
            result = True
        except User.DoesNotExist:
            result = False

    return result


@logger.catch
def set_searching_function(user_id: int, user_searching_function: str) -> None:
    """
    Сеттер для установки функции поиска отелей и флага на дополнительные вопросы.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения
        user_searching_function (str): Принимает введённую пользователем
                                        функцию поиска отелей
    """

    with db:
        if user_searching_function == 'bestdeal':
            # TODO флаг не меняется в БД, проверить
            User(id=User.get_pk_id(user_id), advanced_question_flag=True).save()
        else:
            User(id=User.get_pk_id(user_id), advanced_question_flag=False).save()

        User(id=User.get_pk_id(user_id), searching_function=user_searching_function).save()


@logger.catch
def get_cities(message: Message) -> dict[str, str]:
    """
    Данная функция запрашивает словарь с вариантами городов у функции
    search_location, записывает его в БД и возвращает его.

    Args:
        message (Message): Принимает введённое сообщение пользователя

    Returns (dict): словарь с вариантами городов
    """

    cities = recurring.search_location(message)

    # Добавляем словарь городов в БД
    with db:
        # TODO проверить на автоматическую сериализацию JSON
        User(id=User.get_pk_id(message.from_user.id), cities=cities).save()
        # User.update(cities=json.dumps(cities, indent=4, ensure_ascii=False)
        #             ).where(User.user_id == message.from_user.id).execute()

    return cities


@logger.catch
def set_city_id(user_id: int, user_city: str) -> None:
    """
    Сеттер для установки имени и id искомого пользователем города.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения
        user_city (str): Принимает введённый пользователем город
    """

    with db:
        query = User.select(User.cities, User.id).where(User.user_id == user_id).execute()
        for obj in query:
            for city_name, city_data in obj.cities.items():
                if city_data == user_city:
                    User(id=obj.id, city_id=city_data, city_name=city_name).save()


@logger.catch
def get_city_id(user_id: int) -> str:
    """
    Геттер для получения id искомого пользователем города.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (str): id искомого пользователем города
    """

    return User.get(User.user_id == user_id).city_id


@logger.catch
def get_advanced_question_flag(user_id: int) -> bool | None:
    """
    Геттер для получения значения флага на наличие дополнительных вопросов.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (bool | None): значение флага на наличие дополнительных вопросов
    """

    return User.get(User.user_id == user_id).advanced_question_flag


@logger.catch
def get_hotels(user_id: int) -> tuple[dict[str, dict[str, str | None]] | None, str | None]:
    """
    Данная функция запрашивает словарь с вариантами отелей у функции
    search_hotels, записывает его в БД и возвращает либо кортеж,
    содержащий словарь с найденными отелями, либо ничего.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (tuple): кортеж, содержащий словарь с найденными отелями,
                        либо ничего.
    """

    user_data = User.select().where(User.user_id == user_id).dicts().get()
    searching_func = searching_functions[user_data['searching_function']]
    hotels_data = recurring.search_hotels(data=user_data, searching_func=searching_func)

    if hotels_data[0]:
        # TODO добавить запись в историю
        return hotels_data

    return None, None


def get_address(hotels: dict[str, Any]) -> str:
    """
    Геттер для получения обработанного адреса отеля.

    Args:
        hotels (dict): данные найденных отелей

    Returns (str): адрес отеля
    """

    return ', '.join(list(filter(lambda x: isinstance(x, str) and len(x) > 2, list(hotels['address'].values()))))


def get_landmarks(hotels: dict[str, Any]) -> str:
    """
    Геттер для получения обработанных ориентиров отеля.

    Args:
        hotels (dict): данные найденных отелей

    Returns (str): ориентиры отеля
    """

    return ', '.join(['\n*{label}: {distance}'.format(label=info['label'], distance=info['distance'])
                      for info in hotels['landmarks']])


@logger.catch
def set_hotels_count(user_id: int, user_hotels_count: int) -> None:
    """
    Сеттер для установки кол-ва запрашиваемых пользователем отелей.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения
        user_hotels_count (int): Принимает введённое пользователем кол-во отелей
    """

    if user_hotels_count > 10:
        raise ValueError('ValueError: user_hotels_count must be <= 10')
    else:
        User(id=User.get_pk_id(user_id), hotels_count=user_hotels_count).save()


@logger.catch
def get_hotels_count(user_id: int) -> int | None:
    """
    Геттер для получения кол-ва запрашиваемых пользователем отелей.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (int | None): кол-во запрашиваемых пользователем отелей
    """

    return User.get(User.user_id == user_id).hotels_count


@logger.catch
def set_needed_photo(user_id: int, user_needed_photo: bool | None) -> None:
    """
    Сеттер для установки значения флага, показывающий необходимость
    вывода фотографий отелей.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения
        user_needed_photo (bool | None): Принимает решение пользователя
                                            на вывод фотографий отелей
    """

    User(id=User.get_pk_id(user_id), needed_photo=user_needed_photo).save()


@logger.catch
def get_needed_photo(user_id: int) -> bool | None:
    """
    Геттер для получения значения флага, показывающий необходимость
    вывода фотографий отелей.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (bool | None): значение флага, показывающий необходимость
                            вывода фотографий отелей.
    """

    return User.get(User.user_id == user_id).needed_photo


@logger.catch
def set_photos_count(user_id: int, user_photos_count: int) -> None:
    """
    Сеттер для установки кол-ва фотографий для каждого отеля.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения
        user_photos_count (int): Принимает введённое пользователем кол-во фото
    """

    if user_photos_count > 10:
        raise ValueError('ValueError: user_photos_count must be <= 10')
    else:
        User(id=User.get_pk_id(user_id), photos_count=user_photos_count).save()


@logger.catch
def get_photos_count(user_id: int) -> int | None:
    """
    Геттер для получения кол-ва фотографий для каждого отеля.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (int | None): кол-во фотографий для каждого отеля.
    """

    return User.get(User.user_id == user_id).photos_count


@logger.catch
def get_photos(user_id: int, hotel_id: int, text: str) -> list[InputMediaPhoto]:
    """
    Данная функция запрашивает список url-адресов фотографий отеля
    у функции search_photos и возвращает список фотографий отеля.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения
        hotel_id (int): Принимает id отеля
        text (str): Принимает информацию об отеле

    Returns (list): Возвращает список фотографий отеля
    """

    user_data = User.select().where(User.user_id == user_id).dicts().get()
    photos = recurring.search_photos(data=user_data, hotel_id=hotel_id)
    hotels_photos = list()

    for photo in photos:
        if not hotels_photos:
            hotels_photos.append(InputMediaPhoto(caption=text,
                                                 media=photo['baseUrl'].replace('{size}', 'w'),
                                                 parse_mode='HTML'
                                                 )
                                 )
        else:
            hotels_photos.append(InputMediaPhoto(media=photo['baseUrl'].replace('{size}', 'w')))

    return hotels_photos


@logger.catch
def set_language(user_id: int, user_language: str) -> None:
    """
    Сеттер для установки языка пользователя и флага языка.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения
        user_language (int): Принимает введённый пользователем язык
    """

    User(id=User.get_pk_id(user_id), language=user_language, lang_flag=True).save()


@logger.catch
def get_language(user_id: int) -> str:
    """
    Геттер для получения языка пользователя.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (str): язык пользователя
    """

    return User.get(User.user_id == user_id).language


@logger.catch
def set_currency(user_id: int, user_currency: str) -> None:
    """
    Сеттер для установки валюты пользователя и флага валюты.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения
        user_currency (int): Принимает введённую пользователем валюту
    """

    User(id=User.get_pk_id(user_id), currency=user_currency, cur_flag=True).save()


@logger.catch
def get_currency(user_id: int) -> str:
    """
    Геттер для получения валюты пользователя.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (str): валюту пользователя
    """

    return User.get(User.user_id == user_id).currency


@logger.catch
def add_user(user_id: int, first_name: str, last_name: str, date: int) -> None:
    """
    Функция, которая добавляет пользователя в БД.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения
        first_name (str): Принимает имя пользователя из его команды или сообщения
        last_name (str): Принимает фамилию пользователя из его команды или сообщения
        date (int): Принимает дату команды или сообщения в формате Timestamp
    """

    User(user_id=user_id, first_name=first_name, last_name=last_name, join_date=date).save()


@logger.catch
def add_message(user_id: int,  date: int, command: str = '', message: str = '') -> None:
    """
    Функция, которая добавляет введённые команды и сообщения пользователя в БД.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения
        command (str): Принимает введённую команду пользователя
        message (str): Принимает введённое сообщение пользователя
        date (int): Принимает дату команды или сообщения в формате Timestamp
    """

    User(user_id=user_id, commands=command, messages=message, date=date).save(force_insert=True)


# TODO продумать взаимодействие с Историей (что хранить и что выводить)
# @logger.catch
# def get_history(connect: Connection, user_id: int, within: str = 'all', limit: int = 10) -> list:
#     """
#     Функция, которая получает список команд и сообщений, введённых пользователем в БД.
#
#     Args:
#         connect (Connection): Принимает объект Connection, который по сути
#                                 является менеджером контекста, обеспечивающим
#                                 подключение к файлу БД SQLite
#
#         user_id (int): Принимает id пользователя из его команды или сообщения
#
#         within (str): Принимает значения day(день), week(неделя), month(месяц),
#                         за которое нужно показывать историю (по умолчанию: all)
#
#         limit (int): Ограничение кол-ва выводимых строк (по умолчанию: 10)
#
#
#     Returns (list): Возвращает список команд, сообщений и запросов пользователя
#     """
#
#     cursor = connect.cursor()
#
#     if within == 'day':
#         result = cursor.execute("""
#             SELECT date, commands, messages, requests FROM user_messages
#             WHERE user_id = ? AND date BETWEEN datetime('now', 'start of day') AND datetime('now', 'localtime')
#             ORDER BY date LIMIT ?
#             """, (user_id, limit))
#     elif within == 'week':
#         result = cursor.execute("""
#             SELECT date, commands, messages, requests FROM user_messages
#             WHERE user_id = ? AND date BETWEEN datetime('now', '-6 days') AND datetime('now', 'localtime')
#             ORDER BY date LIMIT ?
#             """, (user_id, limit))
#     elif within == 'month':
#         result = cursor.execute("""
#             SELECT date, commands, messages, requests FROM user_messages
#             WHERE user_id = ? AND date BETWEEN datetime('now', 'start of month') AND datetime('now', 'localtime')
#             ORDER BY date LIMIT ?
#             """, (user_id, limit))
#     else:
#         result = cursor.execute("""
#             SELECT date, commands, messages, requests
#             FROM user_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?
#             """, (user_id, limit))
#
#     return result.fetchall()
#


if __name__ == '__main__':

    # Создаём аргумент force для командной строки
    parser = argparse.ArgumentParser()
    parser.add_argument('--force',
                        action='store_true',
                        help='ВНИМАНИЕ! Аргумент "--force" полностью обнуляет все таблицы в БД'
                        )

    # Принимаем аргумент force из командной строки
    args = parser.parse_args()
    user_args = args.force

    if user_args:
        init_db(force=user_args)
        logger.info('Таблицы БД были полностью удалены и созданы заново')

    # TODO удалить (тесты для наладки)
    # set_city_id(user_id=309881753, user_city='Ереван, Армения')
    # set_city_id(user_id=316776650, user_city='Кентрон, Армения')
    # set_searching_function(user_id=309881753, user_searching_function='bestdeal')
    # get_advanced_question_flag(user_id=309881753)
    # get_hotels(user_id=309881753)
    # set_hotels_count(user_id=309881753, user_hotels_count=5)

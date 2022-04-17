"""
Модуль для работы с БД.
Содержит функции для чтения из БД и записи данных в БД.
"""

import argparse
import datetime as dt
from typing import Any

from loguru import logger
from playhouse.sqlite_ext import *
from telebot.types import Message, InputMediaPhoto

from commands import recurring, hilowprice, bestdeal
from commands.history import get_hotels_for_history
from config import DATABASE


# Подключаемся к БД
db = SqliteExtDatabase(DATABASE)


searching_functions = {'lowprice': hilowprice.lowprice,
                       'highprice': hilowprice.highprice,
                       'bestdeal': bestdeal.bestdeal
                       }


class ModelBase(Model):
    """
    Класс ModelBase, наследуется от класса Model библиотеки peewee.
    Дочерние классы: User и History.

    Данный класс содержит одинаковые поля таблиц и ссылку на БД
    для дочерних классов.
    """

    id = AutoField()

    class Meta:
        database = db


class User(ModelBase):
    """
    Модель, описывающая таблицу БД "users".
    Данная таблица необходима для регистрации новых пользователей бота,
    а также для сохранения выбранных ими параметров и настроек.
    """

    user_id = IntegerField(null=True, constraints=[SQL("UNIQUE ON CONFLICT IGNORE")])
    first_name = CharField(max_length=64, null=True)
    last_name = CharField(max_length=64, null=True)
    join_date = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
    cities = JSONField(null=True, constraints=[SQL("DEFAULT None")])
    city_id = IntegerField(null=True, constraints=[SQL("DEFAULT None")])
    city_name = CharField(max_length=50, null=True, constraints=[SQL("DEFAULT None")])
    date_in = DateField(null=True, constraints=[SQL("DEFAULT None")])
    date_out = DateField(null=True, constraints=[SQL("DEFAULT None")])
    hotels_count = IntegerField(null=True, constraints=[SQL("DEFAULT None")])
    needed_photo = BooleanField(null=True, constraints=[SQL("DEFAULT False")])
    photos_count = IntegerField(null=True, constraints=[SQL("DEFAULT None")])
    price_range = CharField(max_length=30, null=True, constraints=[SQL("DEFAULT None")])
    dist_range = CharField(max_length=10, null=True, constraints=[SQL("DEFAULT None")])
    language = CharField(max_length=8, null=True, constraints=[SQL("DEFAULT ('ru_RU')")])
    lang_flag = BooleanField(null=True, constraints=[SQL("DEFAULT False")])
    currency = CharField(max_length=6, null=True, constraints=[SQL("DEFAULT ('RUB')")])
    cur_flag = BooleanField(null=True, constraints=[SQL("DEFAULT False")])
    advanced_question_flag = BooleanField(null=True, constraints=[SQL("DEFAULT False")])
    searching_function = CharField(max_length=22, null=True, constraints=[SQL("DEFAULT None")])

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

    @classmethod
    def reset_to_default_search_data(cls, user_id: int) -> None:
        """
        Метод, который сбрасывает выбранные пользователем данные
        для поиска отелей в БД к значениям по умолчанию.

        Args:
            user_id (int): Принимает id пользователя из его команды или сообщения
        """

        with db:
            User(id=cls.get_pk_id(user_id), cities=None, city_id=None, city_name=None, date_in=None, date_out=None,
                 hotels_count=None, needed_photo=False, photos_count=None, price_range=None, dist_range=None,
                 language='ru_RU', lang_flag=False, currency='RUB', cur_flag=False, advanced_question_flag=False,
                 searching_function=None).save()


class History(ModelBase):
    """
    Модель, описывающая таблицу БД "user_messages" для сохранения
    истории команд, сообщений и запросов пользователя.
    """

    date = DateTimeField(constraints=[SQL("DEFAULT (datetime('now'))")])
    user_id = ForeignKeyField(model=User, field='user_id')
    commands = CharField(max_length=15, null=True, constraints=[SQL("DEFAULT None")])
    requests = TextField(null=True, constraints=[SQL("DEFAULT None")])
    answers = TextField(null=True, constraints=[SQL("DEFAULT None")])

    class Meta:
        table_name = 'user_messages'

    @classmethod
    def delete_history_data(cls, user_id: int) -> None:
        """
        Метод, который удаляет все записи пользователя из данной таблицы БД

        Args:
            user_id (int): Принимает id пользователя из его команды или сообщения
        """

        with db:
            History.delete().where(History.user_id == user_id).execute()


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


def convert_data(value: Any) -> Any:
    """
    Функция конвертирует значение времени в формате timestamp в
    стандартный формат YYYY-MM-DD HH:MM:SS перед записью в БД.

    Args:
        value (Any): Принимает значение даты и времени в произвольном формате

    Returns (Any): Конвертированное либо нет значение даты и времени
    """

    if isinstance(value, int):
        date_value = dt.datetime.fromtimestamp(value)
        result = date_value.strftime('%Y-%m-%d %H:%M:%S')
    else:
        result = value.strftime('%Y-%m-%d %H:%M:%S')
    return result


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
            User(id=User.get_pk_id(user_id), advanced_question_flag=True).save()
        else:
            User(id=User.get_pk_id(user_id), advanced_question_flag=False).save()

        User(id=User.get_pk_id(user_id), searching_function=user_searching_function).save()


@logger.catch
def get_cities(message: Message) -> dict:
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
        User(id=User.get_pk_id(message.from_user.id), cities=cities).save()

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

    with db:
        return User.get(User.user_id == user_id).city_id


@logger.catch
def get_advanced_question_flag(user_id: int) -> bool | None:
    """
    Геттер для получения значения флага на наличие дополнительных вопросов.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (bool | None): значение флага на наличие дополнительных вопросов
    """

    with db:
        return User.get(User.user_id == user_id).advanced_question_flag


@logger.catch
def set_price_range(user_id: int, price_range: list) -> None:
    """
    Сеттер для установки диапазона цен пользователя.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения
        price_range (list): Принимает ценовой диапазон пользователя
    """

    with db:
        User(id=User.get_pk_id(user_id), price_range=price_range).save()


@logger.catch
def get_price_range(user_id: int) -> list:
    """
    Геттер для получения диапазона цен пользователя.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (list): ценовой диапазон, заданный пользователем
    """

    with db:
        return User.get(User.user_id == user_id).price_range


@logger.catch
def set_distance_range(user_id: int, dist_range: list) -> None:
    """
    Сеттер для установки диапазона расстояний отеля от центра.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения
        dist_range (list): Принимает диапазон расстояний от пользователя
    """

    with db:
        User(id=User.get_pk_id(user_id), dist_range=dist_range).save()


@logger.catch
def get_distance_range(user_id: int) -> list:
    """
    Геттер для получения диапазона расстояний отеля от центра.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (list): диапазон расстояний, заданный пользователем
    """

    with db:
        return User.get(User.user_id == user_id).dist_range


@logger.catch
def get_hotels(user_id: int) -> tuple:
    """
    Данная функция запрашивает словарь с вариантами отелей у функции
    search_hotels, записывает его в БД и возвращает либо кортеж,
    содержащий словарь с найденными отелями, либо ничего.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (tuple): кортеж, содержащий словарь с найденными отелями,
                        либо ничего.
    """

    with db:
        user_data = User.select().where(User.user_id == user_id).dicts().get()

    searching_func = searching_functions[user_data['searching_function']]
    hotels_data = recurring.search_hotels(data=user_data, searching_func=searching_func)

    if hotels_data[0]:
        command_data, found_hotels = get_hotels_for_history(hotels_data=hotels_data, user_data=user_data)
        with db:
            History(
                user_id=user_id,
                commands=user_data['searching_function'],
                requests=command_data,
                answers=found_hotels,
                date=convert_data(dt.datetime.now())
            ).save(force_insert=True)

        return hotels_data

    return None, None


def get_address(hotels: dict) -> str:
    """
    Геттер для получения обработанного адреса отеля.

    Args:
        hotels (dict): данные найденных отелей

    Returns (str): адрес отеля
    """

    return ', '.join(list(filter(lambda x: isinstance(x, str) and len(x) > 2, list(hotels['address'].values()))))


def get_landmarks(hotels: dict) -> str:
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
        with db:
            User(id=User.get_pk_id(user_id), hotels_count=user_hotels_count).save()


@logger.catch
def get_hotels_count(user_id: int) -> int | None:
    """
    Геттер для получения кол-ва запрашиваемых пользователем отелей.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (int | None): кол-во запрашиваемых пользователем отелей
    """

    with db:
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

    with db:
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

    with db:
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
        with db:
            User(id=User.get_pk_id(user_id), photos_count=user_photos_count).save()


@logger.catch
def get_photos_count(user_id: int) -> int | None:
    """
    Геттер для получения кол-ва фотографий для каждого отеля.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (int | None): кол-во фотографий для каждого отеля.
    """

    with db:
        return User.get(User.user_id == user_id).photos_count


@logger.catch
def get_photos(user_id: int, hotel_id: int, text: str) -> list:
    """
    Данная функция запрашивает список url-адресов фотографий отеля
    у функции search_photos и возвращает список фотографий отеля.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения
        hotel_id (int): Принимает id отеля
        text (str): Принимает информацию об отеле

    Returns (list): Возвращает список фотографий отеля
    """

    with db:
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

    with db:
        User(id=User.get_pk_id(user_id), language=user_language, lang_flag=True).save()


@logger.catch
def get_language(user_id: int) -> str:
    """
    Геттер для получения языка пользователя.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (str): язык пользователя
    """

    with db:
        return User.get(User.user_id == user_id).language


@logger.catch
def set_currency(user_id: int, user_currency: str) -> None:
    """
    Сеттер для установки валюты пользователя и флага валюты.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения
        user_currency (int): Принимает введённую пользователем валюту
    """

    with db:
        User(id=User.get_pk_id(user_id), currency=user_currency, cur_flag=True).save()


@logger.catch
def get_currency(user_id: int) -> str:
    """
    Геттер для получения валюты пользователя.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (str): валюту пользователя
    """

    with db:
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

    with db:
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

    with db:
        User(user_id=user_id, commands=command, messages=message, date=date).save(force_insert=True)


@logger.catch
def get_history(user_id: int, within: str) -> Any:
    """
    Функция, которая получает историю команд и запросов пользователя из БД.

    Args:
        user_id (int): Принимает id пользователя из его команды или сообщения

        within (str): Принимает значения last(последний), day(день), week(неделя),
                        за которые нужно запросить историю

    Returns (Model): Возвращает историю команд и запросов пользователя
    """

    if within == 'last':
        with db:
            result = History.select().where(History.user_id == user_id).order_by(History.date.desc()).limit(1).dicts()
    elif within == 'day':
        day_ago = dt.date.today() - dt.timedelta(days=1)
        with db:
            result = History.select().where((History.user_id == user_id) & (History.date >= day_ago)).dicts()
    elif within == 'week':
        day_ago = dt.date.today() - dt.timedelta(days=7)
        with db:
            result = History.select().where((History.user_id == user_id) & (History.date >= day_ago)).dicts()

    return result


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
    else:
        init_db()

    # TODO удалить (тесты для наладки)
    # set_city_id(user_id=309881753, user_city='Ереван, Армения')
    # set_city_id(user_id=316776650, user_city='Кентрон, Армения')
    # set_searching_function(user_id=309881753, user_searching_function='bestdeal')
    # get_advanced_question_flag(user_id=309881753)
    # get_hotels(user_id=309881753)
    # set_hotels_count(user_id=309881753, user_hotels_count=5)

    # with db:
    #     User(
    #         user_id=316776650,
    #         first_name='First_N',
    #         last_name='Last_N',
    #         date=convert_data(value=dt.datetime.now())
    #     ).save(force_insert=True)

    # History.delete_history_data(user_id=309881753)

"""
Модуль для работы с БД.
Содержит функции для чтения из БД и записи данных в БД.
"""

import argparse
import json
from datetime import datetime
import functools
import sqlite3
from sqlite3 import Connection
from typing import Callable, Any

from loguru import logger
import pandas as pd
from telebot.types import Message, InputMediaPhoto

from commands import recurring, hilowprice
from config import DATABASE


searching_functions = {
    'lowprice': hilowprice.lowprice,
    'highprice': hilowprice.highprice
}


@logger.catch
def ensure_connection(func: Callable) -> Callable:
    """
    Декоратор, обеспечивающий потокобезопасное подключение к БД для
    декорируемых им функций.
    Открывает подключение к БД и передаёт её в декорируемую функцию,
    а после выхода из функции закрывает подключение.

    Returns (Callable): Возвращает саму функцию с подключением к БД.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Callable:
        with sqlite3.connect(DATABASE) as connect:
            # Добавляем подключение к БД "connect" в начало кортежа
            # аргументов и передаём аргументы в декорируемую функцию
            my_args = (connect,) + args
            result = func(*my_args, **kwargs)
        return result
    return wrapper


@logger.catch
def convert_timestamp(timestamp: int) -> str:
    """
    Функция, которая конвертирует дату из формата UNIX Timestamp
    в привычный формат DateTime

    Args:
        timestamp (int): Принимает кол-во секунд, прошедших с полуночи
                            1 января 1970 года.

    Returns (str): Возвращает дату в виде строки Y-M-D H:M:S
                    Если значение timestamp не получено, то возвращает
                    пустую строку.
    """

    if timestamp:
        date_value = datetime.fromtimestamp(timestamp)
        result = date_value.strftime('%Y-%m-%d %H:%M:%S')
    else:
        result = ''
    return result


@ensure_connection
@logger.catch
def init_db(connect: Connection, force: bool = False) -> None:
    """
    Функция, которая инициализирует БД.
    Проверяет наличие нужных таблиц, если их нет, то создаёт.
    При вызове с аргументом force=True удаляет таблицы и создаёт их заново.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        force (bool): Если данный аргумент True, то все таблицы удаляются
                        и создаются заново (по умолчанию: False)
    """

    cursor = connect.cursor()

    # Удаление всех таблиц, если аргумент force = True
    if force:
        cursor.execute('DROP TABLE IF EXISTS users')
        cursor.execute('DROP TABLE IF EXISTS user_messages')

    # Создание таблицы для информации о пользователях
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id                      INTEGER         PRIMARY KEY AUTOINCREMENT,
            user_id                 INTEGER         NOT NULL
                                                    UNIQUE ON CONFLICT IGNORE,
            first_name              VARCHAR(64),
            last_name               VARCHAR(64),
            join_date               DATETIME        NOT NULL
                                                    DEFAULT ((DATETIME('now'))),
            cities                  TEXT            DEFAULT None,
            city_id                 INTEGER         DEFAULT None,
            city_name               VARCHAR (50)    DEFAULT None,
            hotels_count            INTEGER         DEFAULT None,
            needed_photo            BOOLEAN         DEFAULT None,
            photos_count            INTEGER         DEFAULT None,
            price_range             VARCHAR (30)    DEFAULT None,
            dist_range              VARCHAR (10)    DEFAULT None,
            language                VARCHAR (8)     DEFAULT ('ru_RU'),
            lang_flag               BOOLEAN         DEFAULT (False),
            currency                VARCHAR (6)     DEFAULT ('RUB'),
            cur_flag                BOOLEAN         DEFAULT (False),
            advanced_question_flag  BOOLEAN         DEFAULT (False),
            searching_function      VARCHAR (22)    DEFAULT None
        )
    """)

    # Создание таблицы для команд и сообщений пользователей,
    # а также запросов и ответов от сервера
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_messages(
            id          INTEGER     PRIMARY KEY AUTOINCREMENT,
            date        DATETIME    NOT NULL
                                    DEFAULT ((DATETIME('now'))),
            user_id     INTEGER     NOT NULL,
            commands    VARCHAR(15),
            messages    VARCHAR(50),
            requests    TEXT,
            answers   TEXT
        )
    """)

    # Сохранить изменения
    connect.commit()

    logger.info('БД инициализирована')


@ensure_connection
@logger.catch
def user_exists(connect: Connection, user_id: int) -> bool:
    """
    Функция, которая проверяет есть ли пользователь в БД.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (bool): Возвращает True, если пользователь уже есть в БД, иначе - False
    """

    cursor = connect.cursor()

    result = cursor.execute('SELECT id FROM users WHERE user_id=:1', {'1': user_id})
    return bool(len(result.fetchall()))


@ensure_connection
@logger.catch
def add_user(connect: Connection, user_id: int, first_name: str, last_name: str, date: int) -> None:
    """
    Функция, которая добавляет пользователя в БД.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения
        first_name (str): Принимает имя пользователя из его команды или сообщения
        last_name (str): Принимает фамилию пользователя из его команды или сообщения
        date (int): Принимает дату команды или сообщения в формате Timestamp
    """

    cursor = connect.cursor()

    # Конвертация даты
    join_date = convert_timestamp(date)

    # Добавление пользователя в БД
    cursor.execute("""
        INSERT INTO users (user_id, first_name, last_name, join_date) VALUES (:1, :2, :3, :4)
        """, {
            '1': user_id,
            '2': first_name,
            '3': last_name,
            '4': join_date
        }
    )

    # Сохранить изменения
    connect.commit()


@ensure_connection
@logger.catch
def get_cities(connect: Connection, message: Message) -> dict[str, str]:
    """
    Данная функция запрашивает словарь с вариантами городов у функции
    search_location, записывает его в БД и возвращает его.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        message (Message): Принимает введённое сообщение пользователя

    Returns:
        словарь с вариантами городов
    """

    cities = recurring.search_location(message)

    cursor = connect.cursor()
    cursor.execute("""
        UPDATE users SET cities=:1 WHERE user_id=:2
        """, {
            '1': json.dumps(cities, indent=4),
            '2': message.from_user.id
        }
    )

    # Сохранить изменения
    connect.commit()

    return cities


@ensure_connection
@logger.catch
def set_city_id(connect: Connection, user_id: int, user_city: str) -> None:
    """
    Сеттер для установки имени и id искомого пользователем города.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения
        user_city (str): Принимает введённый пользователем город
    """

    cursor = connect.cursor()
    cursor.execute('SELECT cities FROM users WHERE user_id=:1', {'1': user_id})  # TODO Подключить peewee
    cities = json.load(cursor.fetchone())
    # cities = cursor.fetchone()

    for city_name, city_data in cities.items():
        if city_data == user_city:
            cursor.execute("""
                UPDATE users SET (city_id=:1, city_name=:2) WHERE user_id=:3
                """, {
                '1': user_city,
                '2': city_name,
                '3': user_id
                }
            )

    # Сохранить изменения
    connect.commit()


@ensure_connection
@logger.catch
def get_city_id(connect: Connection, user_id: int) -> str:
    """
    Геттер для получения id искомого пользователем города.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (str): id искомого пользователем города
    """

    cursor = connect.cursor()
    cursor.execute('SELECT city_id FROM users WHERE user_id=:1', {'1': user_id})
    city_id = cursor.fetchone()

    return city_id


@ensure_connection
@logger.catch
def get_hotels(connect: Connection, user_id: int) -> tuple[dict[str, dict[str, str | None]] | None, str | None]:
    """
    Данная функция запрашивает словарь с вариантами отелей у функции
    search_hotels, записывает его в БД и возвращает либо кортеж,
    содержащий словарь с найденными отелями, либо ничего.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (tuple): кортеж, содержащий словарь с найденными отелями,
                        либо ничего.
    """

    cursor = connect.cursor()

    query = cursor.execute('SELECT * FROM users WHERE user_id=:1', {'1': user_id})

    data_frame = pd.read_sql(query, connect)
    user_data = data_frame.to_dict("user_data")[0]

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


@ensure_connection
@logger.catch
def set_hotels_count(connect: Connection, user_id: int, user_hotels_count: int) -> None:
    """
    Сеттер для установки кол-ва запрашиваемых пользователем отелей.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения
        user_hotels_count (int): Принимает введённое пользователем кол-во отелей
    """

    if user_hotels_count > 10:
        raise ValueError('ValueError: user_hotels_count must be <= 10')
    else:
        cursor = connect.cursor()

        cursor.execute("""
            UPDATE users SET hotels_count=:1 WHERE user_id=:2
            """, {
            '1': user_hotels_count,
            '2': user_id
            }
        )

        # Сохранить изменения
        connect.commit()


@ensure_connection
@logger.catch
def get_hotels_count(connect: Connection, user_id: int) -> int | None:
    """
    Геттер для получения кол-ва запрашиваемых пользователем отелей.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (int | None): кол-во запрашиваемых пользователем отелей
    """

    cursor = connect.cursor()
    cursor.execute('SELECT hotels_count FROM users WHERE user_id=:1', {'1': user_id})
    hotels_count = cursor.fetchone()

    return hotels_count


@ensure_connection
@logger.catch
def set_needed_photo(connect: Connection, user_id: int, user_needed_photo: bool | None) -> None:
    """
    Сеттер для установки значения флага, показывающий необходимость
    вывода фотографий отелей.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения
        user_needed_photo (bool | None): Принимает решение пользователя
                                            на вывод фотографий отелей
    """

    cursor = connect.cursor()

    cursor.execute("""
        UPDATE users SET needed_photo=:1 WHERE user_id=:2
        """, {
        '1': user_needed_photo,
        '2': user_id
        }
    )

    # Сохранить изменения
    connect.commit()


@ensure_connection
@logger.catch
def get_needed_photo(connect: Connection, user_id: int) -> bool | None:
    """
    Геттер для получения значения флага, показывающий необходимость
    вывода фотографий отелей.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (bool | None): значение флага, показывающий необходимость
                            вывода фотографий отелей.
    """

    cursor = connect.cursor()
    cursor.execute('SELECT needed_photo FROM users WHERE user_id=:1', {'1': user_id})
    needed_photo = cursor.fetchone()

    return needed_photo


@ensure_connection
@logger.catch
def set_photos_count(connect: Connection, user_id: int, user_photos_count: int) -> None:
    """
    Сеттер для установки кол-ва фотографий для каждого отеля.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения
        user_photos_count (int): Принимает введённое пользователем кол-во фото
    """

    if user_photos_count > 10:
        raise ValueError('ValueError: user_photos_count must be <= 10')
    else:
        cursor = connect.cursor()

        cursor.execute("""
            UPDATE users SET photos_count=:1 WHERE user_id=:2
            """, {
            '1': user_photos_count,
            '2': user_id
            }
        )

        # Сохранить изменения
        connect.commit()


@ensure_connection
@logger.catch
def get_photos_count(connect: Connection, user_id: int) -> int | None:
    """
    Геттер для получения кол-ва фотографий для каждого отеля.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (int | None): кол-во фотографий для каждого отеля.
    """

    cursor = connect.cursor()
    cursor.execute('SELECT photos_count FROM users WHERE user_id=:1', {'1': user_id})
    photos_count = cursor.fetchone()

    return photos_count


@ensure_connection
@logger.catch
def get_photos(connect: Connection, user_id: int, hotel_id: int, text: str) -> list[InputMediaPhoto]:
    """
    Данная функция запрашивает список url-адресов фотографий отеля
    у функции search_photos и возвращает список фотографий отеля.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения
        hotel_id (int): Принимает id отеля
        text (str): Принимает информацию об отеле

    Returns (list): Возвращает список фотографий отеля
    """

    cursor = connect.cursor()

    query = cursor.execute('SELECT * FROM users WHERE user_id=:1', {'1': user_id})

    data_frame = pd.read_sql(query, connect)
    user_data = data_frame.to_dict("user_data")[0]

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


@ensure_connection
@logger.catch
def set_language(connect: Connection, user_id: int, user_language: str) -> None:
    """
    Сеттер для установки языка пользователя и флага языка.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения
        user_language (int): Принимает введённый пользователем язык
    """

    cursor = connect.cursor()

    cursor.execute("""
        UPDATE users SET (language=:1, lang_flag=:2) WHERE user_id=:3
        """, {
        '1': user_language,
        '2': True,
        '3': user_id
        }
    )

    # Сохранить изменения
    connect.commit()


@ensure_connection
@logger.catch
def get_language(connect: Connection, user_id: int) -> str:
    """
    Геттер для получения языка пользователя.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (str): язык пользователя
    """

    cursor = connect.cursor()
    cursor.execute('SELECT language FROM users WHERE user_id=:1', {'1': user_id})
    language = cursor.fetchone()

    return language


@ensure_connection
@logger.catch
def set_currency(connect: Connection, user_id: int, user_currency: str) -> None:
    """
    Сеттер для установки валюты пользователя и флага валюты.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения
        user_currency (int): Принимает введённую пользователем валюту
    """

    cursor = connect.cursor()

    cursor.execute("""
        UPDATE users SET (currency=:1, cur_flag=:2) WHERE user_id=:3
        """, {
        '1': user_currency,
        '2': True,
        '3': user_id
        }
    )

    # Сохранить изменения
    connect.commit()


@ensure_connection
@logger.catch
def get_currency(connect: Connection, user_id: int) -> str:
    """
    Геттер для получения валюты пользователя.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (str): валюту пользователя
    """

    cursor = connect.cursor()
    cursor.execute('SELECT currency FROM users WHERE user_id=:1', {'1': user_id})
    currency = cursor.fetchone()

    return currency


@ensure_connection
@logger.catch
def get_advanced_question_flag(connect: Connection, user_id: int) -> bool | None:
    """
    Геттер для получения значения флага на наличие дополнительных вопросов.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения

    Returns (bool | None): значение флага на наличие дополнительных вопросов
    """

    cursor = connect.cursor()
    cursor.execute('SELECT advanced_question_flag FROM users WHERE user_id=:1', {'1': user_id})
    advanced_question_flag = cursor.fetchone()

    return advanced_question_flag


@ensure_connection
@logger.catch
def set_searching_function(connect: Connection, user_id: int, user_searching_function: str) -> None:
    """
    Сеттер для установки функции поиска отелей и флага на дополнительные вопросы.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения
        user_searching_function (int): Принимает введённую пользователем
                                        функцию поиска отелей
    """

    cursor = connect.cursor()

    if user_searching_function == 'bestdeal':
        cursor.execute('UPDATE users SET advanced_question_flag=:1 WHERE user_id=:2', {'1': True, '2': user_id})
    else:
        cursor.execute('UPDATE users SET advanced_question_flag=:1 WHERE user_id=:2', {'1': False, '2': user_id})

    cursor.execute("""
        UPDATE users SET searching_function=:1 WHERE user_id=:2
        """, {
            '1': user_searching_function,
            '2': user_id
        }
    )

    # Сохранить изменения
    connect.commit()


@ensure_connection
@logger.catch
def add_message(connect: Connection, user_id: int,  date: int, command: str = '', message: str = '') -> None:
    """
    Функция, которая добавляет введённые команды и сообщения пользователя в БД.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite
        user_id (int): Принимает id пользователя из его команды или сообщения
        command (str): Принимает введённую команду пользователя
        message (str): Принимает введённое сообщение пользователя
        date (int): Принимает дату команды или сообщения в формате Timestamp
    """

    cursor = connect.cursor()

    # Конвертация даты
    converted_date = convert_timestamp(date)

    # Добавление команд и сообщений пользователя в БД
    cursor.execute("""
        INSERT INTO user_messages (user_id, commands, messages, date) VALUES (:1, :2, :3, :4)
        """, {
        '1': user_id,
        '2': command,
        '3': message,
        '4': converted_date
        }
    )

    # Сохранить изменения
    connect.commit()


@ensure_connection
@logger.catch
def get_history(connect: Connection, user_id: int, within: str = 'all', limit: int = 10) -> list:
    """
    Функция, которая получает список команд и сообщений, введённых пользователем в БД.

    Args:
        connect (Connection): Принимает объект Connection, который по сути
                                является менеджером контекста, обеспечивающим
                                подключение к файлу БД SQLite

        user_id (int): Принимает id пользователя из его команды или сообщения

        within (str): Принимает значения day(день), week(неделя), month(месяц),
                        за которое нужно показывать историю (по умолчанию: all)

        limit (int): Ограничение кол-ва выводимых строк (по умолчанию: 10)


    Returns (list): Возвращает список команд, сообщений и запросов пользователя
    """

    cursor = connect.cursor()

    if within == 'day':
        result = cursor.execute("""
            SELECT date, commands, messages, requests FROM user_messages 
            WHERE user_id = ? AND date BETWEEN datetime('now', 'start of day') AND datetime('now', 'localtime') 
            ORDER BY date LIMIT ?
            """, (user_id, limit))
    elif within == 'week':
        result = cursor.execute("""
            SELECT date, commands, messages, requests FROM user_messages 
            WHERE user_id = ? AND date BETWEEN datetime('now', '-6 days') AND datetime('now', 'localtime') 
            ORDER BY date LIMIT ?
            """, (user_id, limit))
    elif within == 'month':
        result = cursor.execute("""
            SELECT date, commands, messages, requests FROM user_messages 
            WHERE user_id = ? AND date BETWEEN datetime('now', 'start of month') AND datetime('now', 'localtime') 
            ORDER BY date LIMIT ?
            """, (user_id, limit))
    else:
        result = cursor.execute("""
            SELECT date, commands, messages, requests
            FROM user_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?
            """, (user_id, limit))

    return result.fetchall()


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

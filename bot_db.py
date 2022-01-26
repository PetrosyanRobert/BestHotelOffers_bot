"""
Модуль для работы с БД
"""
import argparse
import functools
import sqlite3
from sqlite3 import Connection
from typing import Callable
from datetime import datetime

from config import DATABASE
from loguru import logger


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
            id          INTEGER     PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER     NOT NULL
                                    UNIQUE ON CONFLICT IGNORE,
            first_name  VARCHAR(64),
            last_name   VARCHAR(64),
            join_date   DATETIME    NOT NULL
                                    DEFAULT ((DATETIME('now')))
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
            responses   TEXT
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

    result = cursor.execute('SELECT id FROM users WHERE user_id = ?', (user_id,))
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
        INSERT INTO users (user_id, first_name, last_name, join_date) VALUES (?, ?, ?, ?)
        """, (user_id, first_name, last_name, join_date)
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
        INSERT INTO user_messages (user_id, commands, messages, date) VALUES (?, ?, ?, ?)
        """, (user_id, command, message, converted_date)
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

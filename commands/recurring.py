"""
Модуль, который содержит повторяющиеся функции
для команд /lowprice, /highprice, /bestdeal.
"""

from datetime import date
import json
import re
from typing import Callable, Any

from loguru import logger
import requests
from telebot.types import Message

from config import API_HOST, API_KEY


# Ссылки, которые используются для поиска города, отеля и фотографии
city_url = 'https://hotels4.p.rapidapi.com/locations/v2/search'
hotel_url = 'https://hotels4.p.rapidapi.com/properties/list'
photo_url = 'https://hotels4.p.rapidapi.com/properties/get-hotel-photos'

# TODO не забыть после тестов удалить ссылки на url Postman Mock server
# city_url = 'https://71e385c7-4d1e-4c1d-8fa7-09b16043b9ab.mock.pstmn.io/locations/v2/search'
# hotel_url = 'https://71e385c7-4d1e-4c1d-8fa7-09b16043b9ab.mock.pstmn.io/properties/list'
# photo_url = 'https://71e385c7-4d1e-4c1d-8fa7-09b16043b9ab.mock.pstmn.io/properties/get-hotel-photos'


# Заголовки запроса при обращении к rapidapi.com
headers = {'x-rapidapi-host': API_HOST,
           'x-rapidapi-key': API_KEY
           }


@logger.catch
def search_location(message: Message) -> dict:
    """
    Функция, которая формирует и отправляет запрос на поиск городов
    к Hotels API и возвращает словарь с вариантами городов.

    Args:
        message (Message): Принимает объект-сообщение от Telegram

    Returns:
        словарь с вариантами городов
    """

    querystring = {"query": message.text, "locale": "ru_RU"}

    response = requests.request("GET", city_url, headers=headers, params=querystring, timeout=10)

    # TODO Добавить проверку статус кода 200 OK и получения JSON данных
    # if response.status_code == 200:
    #     pass
    # else:
    #     raise Exception()

    # или же так:

    # match response.status_code:
    #     case 200:
    #         pass
    #     case ???

    data = json.loads(response.text)

    cities = {', '.join((city['name'], re.findall('(\\w+)[\n<]', city['caption'] + '\n')[-1])): city['destinationId']
              for city in data['suggestions'][0]['entities']}

    return cities


@logger.catch
def search_hotels(data: dict, searching_func: Callable) -> tuple:
    """
    Функция, которая формирует и отправляет запрос на поиск отелей
    к Hotels API и возвращает кортеж, содержащий словарь с найденными отелями.

    Args:
        data (dict): критерии поиска, заданные пользователем
        searching_func (Callable): сама функция, выполняющая http-запрос

    Returns:
        кортеж, содержащий словарь с найденными отелями
    """

    if data['searching_function'] == 'bestdeal':
        hotels_data = searching_func(user_city_id=data['city_id'],
                                     language=data['language'],
                                     currency=data['currency'],
                                     hotels_count=data['hotels_count'],
                                     hotel_url=hotel_url,
                                     headers=headers,
                                     price_range=data['price_range'],
                                     dist_range=data['dist_range'],
                                     check_in=data['date_in'],
                                     check_out=data['date_out']
                                     )
    else:
        hotels_data = searching_func(user_city_id=data['city_id'],
                                     language=data['language'],
                                     currency=data['currency'],
                                     hotels_count=data['hotels_count'],
                                     hotel_url=hotel_url,
                                     headers=headers,
                                     check_in=data['date_in'],
                                     check_out=data['date_out']
                                     )

    return hotels_data


@logger.catch
def search_photos(data: dict, hotel_id: int) -> list:
    """
    Функция, которая формирует и отправляет запрос на поиск фотографий
    отелей к Hotels API и возвращает список url-адресов фотографий отеля.

    Args:
        data (dict): критерии поиска, заданные пользователем
        hotel_id (int): id отеля

    Returns:
        список url-адресов фотографий отеля
    """

    querystring = {"id": "{}".format(hotel_id)}

    response = requests.request("GET", photo_url, headers=headers, params=querystring, timeout=10)

    # TODO Добавить проверку статус кода 200 OK и получения JSON данных

    photo_data = json.loads(response.text)
    photos_address = photo_data["hotelImages"][:data['photos_count']]

    return photos_address

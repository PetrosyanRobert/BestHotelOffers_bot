"""
Модуль, описывающий 2 команды бота: /lowprice и /highprice.
Содержит функции для получения списка самых дешёвых или дорогих отелей
в выбранном городе.
"""

import json
import re

from loguru import logger
import requests


@logger.catch
def lowprice(**ud) -> tuple:
    """
    Функция, которая формирует и отправляет HTTP-запрос вариантов самых
    дешёвых отелей к Hotels API и возвращает либо кортеж, либо ничего.

    Args:
        **ud: (сокр. от UserData) - Именованные аргументы, где
            user_city_id (str): id города
            language (str): язык пользователя
            currency (str): валюта пользователя
            hotels_count (int): кол-во отелей
            hotel_url (str): ссылка на отель
            headers (dict): необходимые заголовки
            check_in (str): дата заезда
            check_out (str): дата выезда

    Returns:
        кортеж, содержащий словарь с найденными отелями
    """

    querystring = {"destinationId": ud['user_city_id'], "pageNumber": "1", "pageSize": str(ud['hotels_count']),
                   "checkIn": ud['check_in'], "checkOut": ud['check_out'], "adults1": "1", "sortOrder": "PRICE",
                   "locale": "{}".format(ud['language']), "currency": ud['currency']
                   }

    url = (f"""https://hotels.com/search.do?destination-id={ud['user_city_id']}&q-check-in={ud['check_in']}
&q-check-out={ud['check_out']}&q-rooms=1&q-room-0-adults=2&q-room-0-children=0&sort-order={querystring["sortOrder"]}""")

    response = requests.request("GET", ud['hotel_url'], headers=ud['headers'], params=querystring, timeout=10)

    if response.status_code == requests.codes.ok:
        check = re.search(r'(?<=,)\"results\".+?(?=,\"pagination)', response.text)

        if check:
            data = json.loads(response.text)
            hotels_catalog = data['data']['body']['searchResults']['results']

            if not hotels_catalog:
                return None, None

            hotels_glossary = {
                hotel['name']: {
                    'id': hotel['id'], 'name': hotel['name'], 'stars': hotel['starRating'], 'address': hotel['address'],
                    'landmarks': hotel['landmarks'], 'price': hotel['ratePlan']['price'].get('current')
                    if hotel.get('ratePlan', None)
                    else '-', 'coordinate': '+'.join(map(str, hotel['coordinate'].values()))
                } for hotel in hotels_catalog
            }

            return hotels_glossary, url
        else:
            raise ValueError('Ошибка сервера! В JSON ключи не обнаружены.')
    else:
        raise ValueError('Ошибка сервера! Статус код не "200 ОК".')


@logger.catch
def highprice(**ud) -> tuple:
    """
    Функция, которая формирует и отправляет HTTP-запрос вариантов самых
    дорогих отелей к Hotels API и возвращает либо кортеж, либо ничего.

    Args:
        **ud: (сокр. от UserData) - Именованные аргументы, где
            user_city_id (str): id города
            language (str): язык пользователя
            currency (str): валюта пользователя
            hotels_count (int): кол-во отелей
            hotel_url (str): ссылка на отель
            headers (dict): необходимые заголовки
            check_in (str): дата заезда
            check_out (str): дата выезда

    Returns:
        кортеж, содержащий словарь с найденными отелями
    """

    querystring = {"destinationId": ud['user_city_id'], "pageNumber": "1", "pageSize": str(ud['hotels_count']),
                   "checkIn": ud['check_in'], "checkOut": ud['check_out'], "adults1": "1",
                   "sortOrder": "PRICE_HIGHEST_FIRST", "locale": "{}".format(ud['language']), "currency": ud['currency']
                   }

    url = (f"""https://hotels.com/search.do?destination-id={ud['user_city_id']}&q-check-in={ud['check_in']}
&q-check-out={ud['check_out']}&q-rooms=1&q-room-0-adults=2&q-room-0-children=0&sort-order={querystring["sortOrder"]}""")

    response = requests.request("GET", ud['hotel_url'], headers=ud['headers'], params=querystring, timeout=10)

    if response.status_code == requests.codes.ok:
        check = re.search(r'(?<=,)\"results\".+?(?=,\"pagination)', response.text)

        if check:
            data = json.loads(response.text)
            hotels_catalog = data['data']['body']['searchResults']['results']

            if not hotels_catalog:
                return None, None

            hotels_glossary = {
                hotel['name']: {
                    'id': hotel['id'], 'name': hotel['name'], 'stars': hotel['starRating'], 'address': hotel['address'],
                    'landmarks': hotel['landmarks'], 'price': hotel['ratePlan']['price'].get('current')
                    if hotel.get('ratePlan', None)
                    else '-', 'coordinate': '+'.join(map(str, hotel['coordinate'].values()))
                } for hotel in hotels_catalog
            }

            return hotels_glossary, url
        else:
            raise ValueError('Ошибка сервера! В JSON ключи не обнаружены.')
    else:
        raise ValueError('Ошибка сервера! Статус код не "200 ОК".')

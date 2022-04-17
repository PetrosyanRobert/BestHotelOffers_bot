"""
Модуль, описывающий команду бота bestdeal.
Выводит топ отелей, наиболее подходящих по цене и расположению от центра
(самые дешёвые и находятся ближе всего к центру)
"""

import json
import re

from loguru import logger
import requests


@logger.catch
def bestdeal(**ud) -> tuple:
    """
    Функция, которая формирует и отправляет HTTP-запрос лучших для
    пользователя отелей к Hotels API и возвращает либо кортеж, либо ничего.

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
            price_range (list): диапазон цен за ночь
            dist_range (list): диапазон расстояний от центра

    Returns (tuple): кортеж, содержащий словарь с найденными отелями
    """

    querystring = {"destinationId": ud['user_city_id'], "pageNumber": "1", "pageSize": str(ud['hotels_count']),
                   "checkIn": ud['check_in'], "checkOut": ud['check_out'], "adults1": "1",
                   "sortOrder": "DISTANCE_FROM_LANDMARK", "locale": "{}".format(ud['language']),
                   "currency": ud['currency'], 'priceMin': min(json.loads(ud['price_range'])),
                   'priceMax': max(json.loads(ud['price_range']))
                   }

    url = (f"""https://hotels.com/search.do?destination-id={ud['user_city_id']}&q-check-in={ud['check_in']}
&q-check-out={ud['check_out']}&q-rooms=1&q-room-0-adults=2&q-room-0-children=0
&f-price-min={min(json.loads(ud['price_range']))}&f-price-max={max(json.loads(ud['price_range']))}
&f-price-multiplier=1&sort-order={querystring["sortOrder"]}""")

    found_hotels = list()

    while len(found_hotels) < ud['hotels_count']:
        try:
            response = requests.request("GET", ud['hotel_url'], headers=ud['headers'], params=querystring, timeout=10)

            data = json.loads(response.text)
            hotels_catalog = data['data']['body']['searchResults']['results']

            if not hotels_catalog:
                return None, None

            for hotel in hotels_catalog:
                distance = re.findall(r'\d[,.]?\d', hotel['landmarks'][0]['distance'])[0].replace(',', '.')

                if float(distance) > float(max(json.loads(ud['dist_range']))):
                    raise ValueError('Превышено максимальное расстояние от центра города')
                elif float(distance) > float(min(json.loads(ud['dist_range']))):
                    found_hotels.append(hotel)

            querystring['pageNumber'] = str(int(querystring.get('pageNumber')) + 1)

        except ValueError:
            break

    hotels_glossary = {
        hotel['name']: {
            'id': hotel['id'], 'name': hotel['name'], 'stars': hotel['starRating'], 'address': hotel['address'],
            'landmarks': hotel['landmarks'], 'price': hotel['ratePlan']['price'].get('current')
            if hotel.get('ratePlan', None)
            else '-', 'coordinate': '+'.join(map(str, hotel['coordinate'].values()))
        } for hotel in found_hotels
    }

    return hotels_glossary, url

"""
Модуль, описывающий 2 команды бота: /lowprice и /highprice.
Содержит функции для получения списка самых дешёвых или дорогих отелей
в выбранном городе.
"""
import json

from loguru import logger
import requests


@logger.catch
def lowprice(user_city_id: str, language: str, currency: str, hotels_value: int, hotel_url: str,
             headers: dict[str, str], today: str) -> tuple[dict[str, dict[str, str | None]] | None, str | None]:
    """
    Функция, которая формирует и отправляет HTTP-запрос вариантов самых
    дешёвых отелей к Hotels API и возвращает либо кортеж, либо ничего.

    Args:
        user_city_id (str): id города
        language (str): язык пользователя
        currency (str): валюта пользователя
        hotels_value (int): кол-во отелей
        hotel_url (str): ссылка на отель
        headers (dict): необходимые заголовки
        today (str): актуальная дата

    Returns:
        кортеж, содержащий словарь с найденными отелями
    """

    querystring = {"destinationId": user_city_id, "pageNumber": "1", "pageSize": str(hotels_value),
                   "checkIn": today, "checkOut": today, "adults1": "1", "sortOrder": "PRICE",
                   "locale": "{}".format(language), "currency": currency}

    response = requests.request("GET", hotel_url, headers=headers, params=querystring, timeout=10)

    url = f"""
https://hotels.com/search.do?destination-id={user_city_id}&q-check-in={today}&q-check-out={today}
&q-rooms=1&q-room-0-adults=2&q-room-0-children=0&sort-order={querystring["sortOrder"]}"""

    data = json.loads(response.text)
    hotels_catalog = data['data']['body']['searchResults']['results']

    if not hotels_catalog:
        return None, None

    hotels_glossary = {
        hotel['name']: {
            'id': hotel.get('id', '-'), 'name': hotel.get('name', '-'), 'address': hotel.get('address', '-'),
            'landmarks': hotel.get('landmarks', '-'), 'price': hotel['ratePlan']['price'].get('current')
            if hotel.get('ratePlan', None)
            else '-', 'coordinate': '+'.join(map(str, hotel['coordinate'].values()))
        } for hotel in hotels_catalog
    }

    return hotels_glossary, url


@logger.catch
def highprice(user_city_id: str, language: str, currency: str, hotels_value: int, hotel_url: str,
              headers: dict[str, str], today: str) -> tuple[dict[str, dict[str, str | None]] | None, str | None]:
    """
    Функция, которая формирует и отправляет HTTP-запрос вариантов самых
    дорогих отелей к Hotels API и возвращает либо кортеж, либо ничего.

    Args:
        user_city_id (str): id города
        language (str): язык пользователя
        currency (str): валюта пользователя
        hotels_value (int): кол-во отелей
        hotel_url (str): ссылка на отель
        headers (dict): необходимые заголовки
        today (str): актуальная дата

    Returns:
        кортеж, содержащий словарь с найденными отелями
    """

    querystring = {"destinationId": user_city_id, "pageNumber": "1", "pageSize": str(hotels_value),
                   "checkIn": today, "checkOut": today, "adults1": "1",
                   "sortOrder": "PRICE_HIGHEST_FIRST", "locale": "{}".format(language), "currency": currency}

    response = requests.request("GET", hotel_url, headers=headers, params=querystring, timeout=10)

    url = f"""
https://hotels.com/search.do?destination-id={user_city_id}&q-check-in={today}&q-check-out={today}
&q-rooms=1&q-room-0-adults=2&q-room-0-children=0&sort-order={querystring["sortOrder"]}"""

    data = json.loads(response.text)
    hotels_catalog = data['data']['body']['searchResults']['results']

    if not hotels_catalog:
        return None, None

    hotels_glossary = {
        hotel['name']: {
            'id': hotel['id'], 'name': hotel['name'], 'address': hotel['address'], 'landmarks': hotel['landmarks'],
            'price': hotel['ratePlan']['price'].get('current')
            if hotel.get('ratePlan', None)
            else '-', 'coordinate': '+'.join(map(str, hotel['coordinate'].values()))
        } for hotel in hotels_catalog
    }

    return hotels_glossary, url

"""
Модуль, описывающий команду бота /history.
Содержит функции для этой команды.
"""


def get_hotels_for_history(hotels_data: tuple, user_data: dict) -> tuple:
    """
    Функция, которая формирует и возвращает список найденных отелей
    для сохранения в БД, согласно введённой команде пользователя.

    Args:
        hotels_data (tuple): кортеж, содержащий словарь с найденными отелями и ссылки на них
        user_data (dict): данные пользователя из БД в виде словаря

    Returns (tuple): кортеж из введённой команды и списка найденных отелей
    """

    result, query_url = hotels_data
    found_hotels = list()

    for hotel_name, hotel_data in result.items():
        found_hotels.append("<a href='{url}'>{name}</a>".format(name=hotel_name,
                                                                url='https://hotels.com/ho' + str(hotel_data['id'])))

    command_data = "<a href='{query_url}'>{city_name}</a>".format(query_url=query_url,
                                                                  city_name=user_data['city_name'])

    return command_data, found_hotels

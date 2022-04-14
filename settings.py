"""
Модуль, который содержит функции начальных установок:
эмодзи, язык, валюта, лимиты.
"""

emoji = {'low': '\U00002198',
         'high': '\U00002197',
         'best': '\U00002705',
         'history': '\U0001F4D3',
         'hotel': '\U0001F3E8',
         'star': '\U00002B50',
         'star_b': '\U00002605',
         'star_w': '\U00002606',
         'address': '\U0001F4CD',
         'price': '\U0001F4B0',
         'total_price': '\U0001F9FE',
         'landmarks': '\U0001F9ED',
         'link': '\U0001F517',
         'settings': '\U0001F527',
         'left': '\U000021E6',
         'right': '\U000021E8'
         }


def star_rating(rating: str) -> str:
    """
    Функция, которая создаёт и возвращает строку из закрашенных и
    незакрашенных звёзд для наглядности вывода категории отеля

    Args:
        rating (str): Принимает рейтинг отеля, полученного от Hotels API

    Returns (str): строка из звёзд
    """

    if int(rating) >= 5:
        return emoji['star_b'] * 5
    else:
        return emoji['star_b'] * int(rating) + emoji['star_w'] * (5 - int(rating))

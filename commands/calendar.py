"""
Модуль пользовательских настроек для календаря.
"""

from settings import emoji
from telegram_bot_calendar import DetailedTelegramCalendar


# Переопределение словаря названий даты DetailedTelegramCalendar
STEPS = {'y': 'год', 'm': 'месяц', 'd': 'день'}


class MyStyleCalendar(DetailedTelegramCalendar):

    # Переопределение стиля кнопок "предыдущий" и "следующий"
    prev_button = emoji['left']
    next_button = emoji['right']

    # Не показывать пустые ячейки при выборе года и месяца
    empty_month_button = ""
    empty_year_button = ""

"""
Главный скрипт main.py
Запускает бота besthoteloffers_bot.py
"""

import os


if __name__ == '__main__':
    try:
        os.system('python besthoteloffers_bot.py')
    except KeyboardInterrupt:
        print('Работа бота была прервана принудительно, нажатием на [Ctrl] + C')

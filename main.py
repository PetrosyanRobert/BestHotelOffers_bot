"""
Главный скрипт main.py
Запускает бота besthoteloffers_bot.py в дочернем процессе
"""

from subprocess import run

from loguru import logger

from config import EXECUTE_CMD


@logger.catch()
def main() -> None:
    """
    Главная функция программы, запускает бота.
    """

    logger.info('Бот запускается...')

    try:
        run(EXECUTE_CMD, shell=True, check=True)
    except KeyboardInterrupt:
        logger.error('Работа бота была прервана принудительно, нажатием на [Ctrl] + C')


if __name__ == '__main__':
    logger.add('Log/debug.log', encoding='utf-8', rotation='1 week', compression='zip')
    main()

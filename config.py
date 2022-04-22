"""
Модуль настройки бота
"""

import os

from dotenv import load_dotenv, find_dotenv

if not find_dotenv():
    exit('Ошибка! Файл ".env" не найден.')
else:
    load_dotenv()

EXECUTE_CMD = os.getenv('EXECUTE_CMD')
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE = os.getenv('DATABASE')
API_HOST = os.getenv('API_HOST')
API_KEY = os.getenv('API_KEY')

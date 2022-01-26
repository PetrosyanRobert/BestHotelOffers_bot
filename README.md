# <p align="center">Best Hotel Offers Bot
___
[comment]: <> (License: )

Telegram-бот для анализа сайта [**Hotels.com**](https://ru.hotels.com/) и поиска подходящих пользователю отелей. <br>Бота можно найти под именем [@best_hotel_offers_bot](http://t.me/best_hotel_offers_bot).

Для самостоятельного запуска бота вам потребуются:

- [Python](https://www.python.org/) 3.10 или выше (сам бот написан на 3.10.1)
- Модуль [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI)
- Модуль [python-dotenv](https://github.com/theskumar/python-dotenv)
- Модуль [loguru](https://github.com/Delgan/loguru)
- База данных sqlite3 (встроен в сам Python)

## Установка

- Создайте у себя файл `.env` (образец файла см. в `env.example`) 
- Получите токен вашего бота от [@BotFather](http://telegram.me/BotFather) и добавьте его в файл `.env`.
- Придумайте название вашей БД и добавьте его в файл `.env` (БД будет создана автоматически при первом запуске бота)
- Установите необходимые библиотеки (рекомендуется использовать `virtualenv`): `pip install -r requirements.txt`

Затем запустите бота из командной строки `python main.py`.


## Работа с БД

Чтобы полностью очистить БД, наберите в командной строке: `python bot_db.py --force`
<br>Данная команда удаляет все таблицы из БД и затем создаёт их заново. 

<br><br>Документация по коду в разработке, добавляется и редактируется по ходу работы над проектом.
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
***
***


# Project Title

One Paragraph of project description goes here

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

What things you need to install the software and how to install them

```
Give examples
```

### Installing

A step by step series of examples that tell you how to get a development env running

Say what the step will be

```
Give the example
```

And repeat

```
until finished
```

End with an example of getting some data out of the system or using it for a little demo

## Running the tests

Explain how to run the automated tests for this system

### Break down into end to end tests

Explain what these tests test and why

```
Give an example
```

### And coding style tests

Explain what these tests test and why

```
Give an example
```

## Deployment

Add additional notes about how to deploy this on a live system

## Built With

* [Dropwizard](http://www.dropwizard.io/1.0.2/docs/) - The web framework used
* [Maven](https://maven.apache.org/) - Dependency Management
* [ROME](https://rometools.github.io/rome/) - Used to generate RSS Feeds

## Contributing

Please read [CONTRIBUTING.md](https://gist.github.com/PurpleBooth/b24679402957c63ec426) for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/your/project/tags). 

## Authors

* **Billie Thompson** - *Initial work* - [PurpleBooth](https://github.com/PurpleBooth)

See also the list of [contributors](https://github.com/your/project/contributors) who participated in this project.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* Hat tip to anyone whose code was used
* Inspiration
* etc

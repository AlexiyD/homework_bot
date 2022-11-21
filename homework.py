import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s',
    filename='main.log',
)
handler = [logging.FileHandler('log.txt'),
           logging.StreamHandler(sys.stdout)]

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('отправка сообщения в TG')
    except telegram.TelegramError as error:
        logging.error(f'отправить сообщение в TG не удолось: {error}')
        raise Exception(error)


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        raise ReferenceError('Ошибка ответа API')
    return response.json()


def check_response(response):
    if not isinstance(response, dict):
        raise TypeError('В API нет словоря')
    if 'homeworks' not in response:
        raise KeyError('Ключ отсутствует в словаре')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Ключа homeworks не передал список')
    return response['homeworks']


def parse_status(homework):
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if 'homework_name' not in homework:
        raise KeyError('Ключ отсутствует в словаре')
    if 'status' not in homework:
        raise KeyError('Ключ отсутствует в словаре!')
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError(f'Неизвестен статус {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise KeyError('Отсутствие ключа')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if not homework:
                message = 'Обновлений нет'
            else:
                message = parse_status(homework[0])
            current_timestamp = response['current_date']
        except ReferenceError as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        except KeyError as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        except TypeError as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        finally:
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

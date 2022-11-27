import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logging.info('начали отправку сообщения в TG')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError as error:
        logging.error(f'отправить сообщение в TG не удолось: {error}')
        raise Exception(error)
    else:
        logging.debug('отправка сообщения в TG!')


def get_api_answer(current_timestamp):
    """Получить статус домашней работы."""
    timestamp = current_timestamp or int(time.time())
    request_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }

    try:
        response = requests.get(**request_params)
        logging.debug('Отправлен запрос к эндпоинту API-сервиса')
    except requests.ConnectionError:
        raise ConnectionError('Подключение к Интернету отсутствует')
    except Exception as error:
        logging.error(f'API недоступен.Ошибка от сервера: {error}')
        send_message(f'API недоступен. Ошибка от сервера: {error}')
    if response.status_code != HTTPStatus.OK:
        logging.error(f'Код ответа не 200: {response.status_code}')
        raise requests.exceptions.RequestException(
            f'Код ответа не 200: {response.status_code}.'
            f'Текст: {response.text}.'
        )
    return response.json()


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise TypeError('В API нет словоря')
    if 'homeworks' not in response:
        raise KeyError('Ключ отсутствует в словаре')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Ключа "homeworks" не передал список')
    return response['homeworks']


def parse_status(homework):
    """Информация о статусе работы."""
    if 'homework_name' not in homework:
        raise KeyError('в ответе API нет ключа `homework_name`')
    homework_name = homework['homework_name']
    if 'status' not in homework:
        raise KeyError('Ключ отсутствует в словаре!')
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(f'Неизвестен статус {homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return(f'Изменился статус проверки работы "{homework_name}". {verdict}')


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('отсутствие переменных окружения!')
        sys.exit('отсутствие переменных окружения!')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    current_response = ''
    prev_response = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework is None:
                message = 'Список работ пуст!'
                send_message(bot, message)
            current_response = homework
            if current_response != prev_response:
                prev_response = current_response
                message = parse_status(homework[0])
                send_message(bot, message)
            else:
                logging.debug('Статус не обновлен')
            current_timestamp = response.get('current_date', current_timestamp)
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
            send_message(bot, f'отсутствие переменных окружения! {error}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format=('%(asctime)s, %(levelname)s, %(name)s, %(message)s',
                '%(filename)s, %(funcName)s, %(lineno)d,',)
    )
    handler = [logging.FileHandler('log.txt'),
               logging.StreamHandler(sys.stdout)]
    main()

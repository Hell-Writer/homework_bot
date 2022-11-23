import logging
import os
import time
from http import HTTPStatus
from sys import exit

import requests
import telegram
from dotenv import load_dotenv

from custom_errors import ApiError, SendMessageError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('BASE_CHAT_ID')

RETRY_TIME = 600
RETRY_PERIOD = RETRY_TIME
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

URL = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

logging.basicConfig(
    filename='main.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        raise SendMessageError('Проблема с отправкой сообщения')
    else:
        logging.info('Сообщение отправлено')


def get_api_answer(current_timestamp):
    """Получаем ответ от сервера."""
    try:
        timestamp = current_timestamp or int(time.time())
        params = {'from_date': timestamp}
        headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
        response = requests.get(URL, headers=headers, params=params)
        logging.debug('Отправлен запрос на сервер')
        if response.status_code == HTTPStatus.OK:
            return response.json()
        else:
            raise ApiError('Проблема с ответом API')
    except Exception:
        raise ApiError('Проблема с подключением к API')


def check_response(response):
    """Проверка типов данных."""
    if not isinstance(response, dict):
        raise TypeError('Неверный тип данных в JSON полученном с API')
    homework = response.get('homeworks')
    if 'homeworks' not in response.keys():
        raise KeyError('Неверный ключ ДЗ')
    if 'current_date' not in response.keys():
        raise KeyError('Неверный ключ времени')
    if not isinstance(homework, list):
        raise TypeError('Неверный тип данных в списке ДЗ полученном с API')
    return homework


def parse_status(homework):
    """Статус проверки дз."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'homework_name' not in homework.keys():
        raise KeyError('Нет ключа homework_name')
    if 'status' not in homework.keys():
        raise KeyError('Нет ключа status')
    if homework_status not in HOMEWORK_STATUSES.keys():
        raise KeyError(f'''Недокументированный статус домашней работы
        {homework_name}, обнаруженный в ответе API''')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    prev_message = ''
    if not check_tokens():
        logging.critical('Отсутствуют переменные окружения')
        exit('Отсутствуют переменные окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp - RETRY_TIME)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                logging.debug('Домашек нет')
            current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        else:
            if message != prev_message:
                response = send_message(bot, message)
                if response == message:
                    logging.debug('Сообщение отправлено')
                else:
                    logging.error('Сообщение не отправлено')
                prev_message = message
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

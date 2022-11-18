import logging
import os
import time
from http import HTTPStatus
import requests
import telegram
from dotenv import load_dotenv

from custom_errors import SendMessageError, ApiError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('BASE_CHAT_ID')

RETRY_TIME = 600
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

# Для ревьюера
# Я не стал проверять наличие ключа в словарях,
# т.к. по дефолту без ключа ставил значение None, а затем
# просто проверял значение на соответствие типу.


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        logging.error('Сообщение не отправлено')
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
    homework = response.get('homeworks', None)
    if not isinstance(homework, list):
        raise TypeError('Неверный тип данных в списке ДЗ полученном с API')
    else:
        return response['homeworks']
    if response['homeworks'] == []:
        logging.debug('Отсутствие в ответе новых статусов')


def parse_status(homework):
    """Статус проверки дз."""
    homework_name = homework.get('homework_name', None)
    homework_status = homework.get('status', None)
    verdict = HOMEWORK_STATUSES.get(homework_status, None)
    if homework_name is None or verdict is None:
        raise KeyError('''Недокументированный статус домашней работы,
            обнаруженный в ответе API''')
    else:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time.time())
    else:
        logging.critical('Отсутствуют переменные окружения')
        raise EnvironmentError('Отсутствуют переменные окружения')

    while True:
        try:
            response = get_api_answer(current_timestamp - RETRY_TIME)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                logging.info('Сообщение отправлено')
            else:
                logging.info('Домашек нет')
            current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        else:
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

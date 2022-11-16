import logging
import os
import datetime
import time

import requests
from dotenv import load_dotenv
import telegram
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater


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


def send_message(bot, message):
    """Отправка сообщения"""
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """Получаем ответ от сервера"""
    try:
        timestamp = current_timestamp or int(time.time())
        params = {'from_date': timestamp}
        headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
        response = requests.get(URL, headers=headers, params=params)
        return response.json()
    except Exception:
        logging.error('Проблема с подключением к API')


def check_response(response):
    """Проверка типов данных"""
    if type(response) != dict:
        logging.error('Неверный тип данных в JSON полученном с API')
        return []
    elif type(response['homeworks']) != list:
        logging.error('Неверный тип данных в списке ДЗ полученном с API')
        return []
    else:
        return response['homeworks']
    if response['homeworks'] == []:
        logging.debug('Отсутствие в ответе новых статусов')
        

def parse_status(homework):
    """Статус проверки дз"""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status in HOMEWORK_STATUSES.keys():
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        logging.error('Недокументированный статус домашней работы, обнаруженный в ответе API')
        return 'Ошибка'


def check_tokens():
    """Проверка переменных окружения"""
    if len(PRACTICUM_TOKEN)==0:
        logging.critical('Отсутствует переменная окружения PRACTICUM_TOKEN')
        return False
    elif len(TELEGRAM_TOKEN)==0:
        logging.critical('Отсутствует переменная окружения TELEGRAM_TOKEN')
        return False
    elif len(TELEGRAM_CHAT_ID)==0:
        logging.critical('Отсутствует переменная окружения TELEGRAM_CHAT_ID')
        return False
    else:
        return True



def main():
    """Основная логика работы бота."""

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp - RETRY_TIME)
            homeworks = check_response(response)
            for homework in homeworks:
                message = parse_status(homework)
                try:
                    send_message(bot, message)
                    logging.info('Сообщение отправлено')
                except:
                    logging.error('Сообщение не отправлено')
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error('Неизвестный сбой в работе программы')
            time.sleep(RETRY_TIME)
        else:
            logging.error('Неизвестный сбой в работе сервера')
            time.sleep(RETRY_TIME)
            


if __name__ == '__main__' and check_tokens():
    main() 

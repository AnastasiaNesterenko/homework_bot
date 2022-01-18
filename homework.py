import logging

import os

import requests

import time

import telegram

from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)
handler.setLevel(level=logging.INFO)
handler.setFormatter(formatter)


def send_message(bot, message):
    """Бот оправляет сообщение о статусе работы."""
    if bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message):
        pass
    else:
        raise Exception('Сообщение не отправленно')


def get_api_answer(current_timestamp):
    """Бот делает запрос на сайт яндекса,
    либо по дате на текущий момент,
    либо по дате последней проверки."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == 200:
        response = response.json()
        return response
    else:
        raise Exception('Недоступность сайта в переменной ENDPOINT')


def check_response(response):
    """Бот проверяет правильность запроса -
    существования полей в словаре запроса."""
    if response['homeworks'] \
            or response['homeworks'] == [] \
            and response['current_date']:
        homeworks = response['homeworks']
        homework = homeworks[0]
        return homework
    else:
        raise Exception('Недоступнойсть ключей')


def parse_status(homework):
    """Бот возвращает статус работы."""
    if 'homework_name' in homework:
        if 'status' in homework:
            if homework['status'] in HOMEWORK_STATUSES:
                homework_name = homework['homework_name']
                homework_status = homework['status']
                verdict = HOMEWORK_STATUSES[homework_status]
                return f'Изменился статус проверки работы "{homework_name}". {verdict}'
            else:
                raise Exception(
                    'Статус домашней работы отсутсвует '
                    'в словаре HOMEWORK_STATUSES'
                )
        else:
            raise Exception('Отсутствует status домашней работы в запросе')
    else:
        raise KeyError('Отсутствует homework_name домашней работы')


def check_tokens():
    """Бот проверяет наличие переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    else:
        return False


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    check_tokens()
    status = ''
    old_message = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            if response['homeworks']:
                homework = check_response(response)
                if homework['status'] != status:
                    message = parse_status(homework)
                    send_message(bot, message)
                    logger.info('Сообщение отправленно')
                else:
                    logger.debug('Отсутсие изменения статуса')
                status = homework['status']
            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != old_message:
                send_message(bot, message)
            old_message = message
            time.sleep(RETRY_TIME)
        else:
            ...


if __name__ == '__main__':
    main()

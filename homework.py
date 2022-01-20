import json
import logging
import os
import time
from http import HTTPStatus

import requests
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
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info('Сообщение отправленно')
    except telegram.TelegramError:
        logger.error('Сообщение не отправлено')


def get_api_answer(current_timestamp):
    """
    Бот делает запрос на сайт яндекса.
    Либо по дате на текущий момент.
    Либо по дате последней проверки.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code == HTTPStatus.OK:
            try:
                response = response.json()
                return response
            except json.decoder.JSONDecodeError:
                raise Exception('Запрос не преобразовался в формат JSON')
        else:
            raise Exception('Код доступа не равен 200')
    except requests.exceptions.HTTPError:
        raise Exception('Ошибка ответа (состояния) сервера')
    except requests.ConnectionError:
        raise Exception('Ошибка соединения')
    except requests.exceptions.Timeout:
        raise Exception('Ошибка времени ожидания')
    except requests.exceptions.RequestException:
        raise Exception('Ошибка запроса')


def check_response(response):
    """
    Бот проверяет правильность запроса.
    Существования полей в словаре запроса.
    """
    if not isinstance(response, dict):
        raise TypeError('"response" не является словарем')
    if 'homeworks' not in response:
        raise TypeError('Ключ "homeworks" отсутсвует в "response"')
    if 'current_date' not in response:
        raise TypeError('Ключ "current_date" отсутсвует в "response"')
    homeworks = response['homeworks']
    homework = homeworks[0]
    return homework


def parse_status(homework):
    """Бот возвращает статус работы."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует коюч "homework_name" в словаре')
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ "status" в словаре')
    if homework['status'] not in HOMEWORK_STATUSES:
        raise Exception(
            'Статус домашней работы '
            'отсутсвует в словаре HOMEWORK_STATUSES'
        )
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    return (f'Изменился статус проверки '
            f'работы "{homework_name}". {verdict}')


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
    if not check_tokens():
        logger.critical('Отсутствуют переменные окружения')
        exit()
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


if __name__ == '__main__':
    main()

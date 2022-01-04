import sys
import json
from dec import log

sys.path.append('../')

DEFAULT_PORT = 7777
DEFAULT_IP_ADDRESS = '127.0.0.1'
ENCODING = 'utf-8'

# Словари - ответы:
# 200
RESPONSE_200 = {'RESPONSE': 200}
# 400
RESPONSE_400 = {
    'RESPONSE': 400,
    'ERROR': None
}


@log
def get_message(client):
    """
    Утилита приёма и декодирования сообщения принимает байты выдаёт словарь,
    если приняточто-то другое отдаёт ошибку значения
    :param client:
    :return:
    """
    encoded_response = client.recv(4128)
    if isinstance(encoded_response, bytes):
        json_response = encoded_response.decode(ENCODING)
        response = json.loads(json_response)
        if isinstance(response, dict):
            return response
        else:
            print('Ошибка 27 стр')
    else:
        print('Ошибка 29 стр')


@log
def send_message(sock, message):
    """
    Утилита кодирования и отправки сообщения
    принимает словарь и отправляет его
    :param sock:
    :param message:
    :return:
    """

    js_message = json.dumps(message)
    encoded_message = js_message.encode(ENCODING)
    sock.send(encoded_message)

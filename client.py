import time
from socket import *
import json
import sys
from common.settings import *
import logging
import log.client_log_config
from dec import log
import threading
from metaclasses import ClientMaker

CLIENT_LOGGER = logging.getLogger('client')


@log
def get_args():
    try:
        if '-n' in sys.argv:

            client_name = sys.argv[sys.argv.index('-n') + 1]
            CLIENT_LOGGER.info(f'"Имя клиента" {client_name}')
        else:
            client_name = 'default'
        if sys.argv[1]:
            server_address = sys.argv[1]
            server_port = int(sys.argv[2])
            CLIENT_LOGGER.info(f'Установлены: порт:{server_port} адрес {server_address}')
    except:
        server_address = DEFAULT_IP_ADDRESS
        server_port = DEFAULT_PORT
        CLIENT_LOGGER.info('Установлен стандартный порт и адрес')

    return server_address, server_port, client_name


# @log
# def create_message(sock, account_name='Guest'):
#     """
#     Функция запрашивает кому отправить сообщение и само сообщение,
#     и отправляет полученные данные на сервер
#     :param sock:
#     :param account_name:
#     :return:
#     """
#     to_user = input('Введите получателя сообщения: ')
#     message = input('Введите сообщение для отправки: ')
#     message_dict = {
#         'ACTION': 'MESSAGE',
#         'SENDER': account_name,
#         'DESTINATION': to_user,
#         'TIME': time.time(),
#         'MESSAGE_TEXT': message
#     }
#     CLIENT_LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')
#     try:
#         send_message(sock, message_dict)
#         CLIENT_LOGGER.info(f'Отправлено сообщение для пользователя {to_user}')
#     except:
#         CLIENT_LOGGER.critical('Потеряно соединение с сервером.')
#         sys.exit(1)


# @log
# def message_from_server(sock, my_username):
#     """Функция - обработчик сообщений других пользователей, поступающих с сервера"""
#     while True:
#         try:
#             message = get_message(sock)
#             if 'ACTION' in message and message['ACTION'] == 'MESSAGE' and \
#                     'SENDER' in message and 'DESTINATION' in message \
#                     and 'MESSAGE_TEXT' in message and message['DESTINATION'] == my_username:
#                 print(f'\nПолучено сообщение от пользователя {message["SENDER"]}:'
#                       f'\n{message["MESSAGE_TEXT"]}')
#                 CLIENT_LOGGER.info(f'Получено сообщение от пользователя {message["SENDER"]}:'
#                                    f'\n{message["MESSAGE_TEXT"]}')
#             else:
#                 CLIENT_LOGGER.error(f'Получено некорректное сообщение с сервера: {message}')
#         except:
#             CLIENT_LOGGER.error('Критическая ошибка')
#             break


class Interface(threading.Thread, metaclass=ClientMaker):
    def __init__(self, sock, username):

        self.sock = sock
        self.username = username

        super().__init__()

    def run(self):
        """Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения"""
        print('для отправки сообщения - m \n для выхода - x')
        while True:
            command = input('Введите команду: ')
            if command == 'm':
                self.create_message(self.sock, self.username)

            elif command == 'x':
                try:
                    send_message(self.sock, self.create_exit_message())
                except:
                    pass
                print('Завершение соединения.')
                CLIENT_LOGGER.info('Завершение работы по команде пользователя.')
                time.sleep(0.5)
                break
            else:
                print('Команда не распознана, попробойте снова')

    @log
    def create_message(self, sock, username):
        """
        Функция запрашивает кому отправить сообщение и само сообщение,
        и отправляет полученные данные на сервер
        :param sock:
        :param account_name:
        :return:
        """
        to_user = input('Введите получателя сообщения: ')
        message = input('Введите сообщение для отправки: ')
        message_dict = {
            'ACTION': 'MESSAGE',
            'SENDER': self.username,
            'DESTINATION': to_user,
            'TIME': time.time(),
            'MESSAGE_TEXT': message
        }
        CLIENT_LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')
        print(f'Сформирован словарь сообщения: {message_dict}, {self.sock}')
        try:
            send_message(self.sock, message_dict)
            CLIENT_LOGGER.info(f'Отправлено сообщение для пользователя {to_user}')
        except:
            CLIENT_LOGGER.critical('Потеряно соединение с сервером.')
            sys.exit(1)


    def create_exit_message(self):
        return {
            'ACTION': 'EXIT',
            'TIME': time.time(),
            'SENDER': self.username
        }

@log
def process_response_ans(message):
    """
    Функция разбирает ответ сервера на сообщение о присутствии,
    возращает 200 если все ОК или генерирует исключение при ошибке
    :param message:
    :return:
    """
    CLIENT_LOGGER.debug(f'Разбор приветственного сообщения от сервера: {message}')
    if 'RESPONSE' in message:
        if message['RESPONSE'] == 200:
            return '200 : OK'
        elif message['RESPONSE'] == 400:
            print(f'400 : {message["ERROR"]}')


@log
def create_presence(account_name):
    """Функция генерирует запрос о присутствии клиента"""
    out = {
        'ACTION': 'PRESENCE',
        'TIME': time.time(),
        'USER': {
            'ACCOUNT_NAME': account_name
        }
    }
    CLIENT_LOGGER.debug(f'Сформировано {out["ACTION"]} сообщение для пользователя {account_name}')
    return out


class ClientReader(threading.Thread, metaclass=ClientMaker):
    def __init__(self, sock, my_username):
        self.my_username = my_username
        self.sock = sock
        super().__init__()
        print(my_username, sock)

    def run(self):
        while True:
            try:
                message = get_message(self.sock)
                if 'ACTION' in message and message['ACTION'] == 'MESSAGE' and \
                        'SENDER' in message and 'DESTINATION' in message \
                        and 'MESSAGE_TEXT' in message and message['DESTINATION'] == self.my_username:
                    print(f'\nПолучено сообщение от пользователя {message["SENDER"]}:'
                          f'\n{message["MESSAGE_TEXT"]}')
                    CLIENT_LOGGER.info(f'Получено сообщение от пользователя {message["SENDER"]}:'
                                       f'\n{message["MESSAGE_TEXT"]}')
                else:
                    CLIENT_LOGGER.error(f'Получено некорректное сообщение с сервера: {message}')
            except:
                CLIENT_LOGGER.error('Критическая ошибка')
                print('Критическая ошибка')
                break


@log
def main():
    server_address, server_port, client_name = get_args()
    meta_info = f'Запущен клиент с парамертами: адрес сервера: {server_address}, \n' \
                f'порт: {server_port}, имя пользователя: {client_name}'

    CLIENT_LOGGER.info(meta_info)
    print(meta_info)
    try:
        transport = socket(AF_INET, SOCK_STREAM)
        transport.connect((server_address, server_port))
        send_message(transport, create_presence(client_name))
        answer = process_response_ans(get_message(transport))
        print(f'Ответ сервера{answer}')
        # Если соединение с сервером установлено корректно,
        # запускаем клиенский процесс приёма сообщний
        # receiver = threading.Thread(target=message_from_server, args=(transport, client_name))
        receiver = ClientReader(transport, client_name)
        receiver.daemon = True
        receiver.start()
        # затем запускаем отправку сообщений и взаимодействие с пользователем.
        user_interface = Interface(transport, client_name)
        user_interface.daemon = True
        user_interface.start()
        CLIENT_LOGGER.debug('Запущены процессы')
        # Watchdog основной цикл, если один из потоков завершён,
        # то значит или потеряно соединение или пользователь
        # ввёл exit. Поскольку все события обработываются в потоках,
        # достаточно просто завершить цикл.
        while True:
            time.sleep(1)
            if receiver.is_alive() and user_interface.is_alive():
                continue
            break

    except Exception as err:
        print(err)
        CLIENT_LOGGER.error(err)
        sys.exit(1)


if __name__ == '__main__':
    main()

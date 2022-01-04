from socket import *
import json
import sys
from common.settings import *
import logging
import log.server_log_config
from dec import log
import select
import time
from descrptrs import Port
from metaclasses import ServerMaker

SERVER_LOGGER = logging.getLogger('server')


@log
def get_args():
    try:
        if '-p' in sys.argv:
            listen_port = int(sys.argv[sys.argv.index('-p') + 1])
            SERVER_LOGGER.info(f'порт "прослушивания" {listen_port}')
        else:
            listen_port = DEFAULT_PORT
            SERVER_LOGGER.info(f'задан стандартный порт для "прослушивания" {listen_port}')
        if listen_port < 1024 or listen_port > 65535:
            raise ValueError
        if '-a' in sys.argv:
            listen_address = sys.argv[sys.argv.index('-a') + 1]
            SERVER_LOGGER.info(f'адрес "прослушивания" {listen_address}')
        else:
            listen_address = DEFAULT_IP_ADDRESS
            SERVER_LOGGER.info(f'задан стандартный адрес для "прослушивания" {listen_address}')
    except ValueError:
        SERVER_LOGGER.critical('не верно задан порт. Значение должно быть от 1024 до 65535')
        sys.exit(1)
    except:
        SERVER_LOGGER.critical('Ошибка')
        sys.exit(1)

    return listen_address, listen_port


class Server(metaclass=ServerMaker):
    port = Port()

    def __init__(self, listen_address, listen_port):
        # Параметры подключения
        self.addr = listen_address
        self.port = listen_port

        # Список подключённых клиентов.
        self.clients = []

        # Список сообщений на отправку.
        self.messages = []

        # Словарь содержащий сопоставленные имена и соответствующие им сокеты.
        self.names = dict()

    def init_socket(self):
        SERVER_LOGGER.info(
            f'Запущен сервер, порт для подключений: {self.port}, '
            f'адрес с которого принимаются подключения: {self.addr}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')
        # Готовим сокет
        transport = socket(AF_INET, SOCK_STREAM)
        # transport.bind((listen_address, listen_port))
        # transport.settimeout(0.5)

        # transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.bind((self.addr, self.port))
        transport.settimeout(0.5)
        transport.listen(8)
        # Начинаем слушать сокет.
        self.sock = transport
        self.sock.listen()

    @log
    def get_client_message(self, message, messages_list, client, clients, names):
        """
        Обработчик сообщений от клиентов, принимает словарь - сообщение от клиента,
        проверяет корректность, отправляет словарь-ответ в случае необходимости.
        :param message:
        :param messages_list:
        :param client:
        :param clients:
        :param names:
        :return:
        """
        SERVER_LOGGER.debug(f'Разбор сообщения от клиента : {message}')
        # Если это сообщение о присутствии, принимаем и отвечаем
        if 'ACTION' in message and message['ACTION'] == 'PRESENCE' and \
                'TIME' in message and 'USER' in message:
            # Если такой пользователь ещё не зарегистрирован,
            # регистрируем, иначе отправляем ответ и завершаем соединение.
            if message['USER']['ACCOUNT_NAME'] not in self.names.keys():
                self.names[message['USER']['ACCOUNT_NAME']] = client
                send_message(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response['ERROR'] = 'Имя пользователя уже занято.'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return
        # Если это сообщение, то добавляем его в очередь сообщений.
        # Ответ не требуется.
        elif 'ACTION' in message and message['ACTION'] == 'MESSAGE' and \
                'DESTINATION' in message and 'TIME' in message \
                and 'SENDER' in message and 'MESSAGE_TEXT' in message:
            self.messages.append(message)
            return
        # Если клиент выходит
        elif 'ACTION' in message and message['ACTION'] == 'EXIT' and 'ACCOUNT_NAME' in message:
            self.clients.remove(self.names[message['ACCOUNT_NAME']])
            self.names[message['ACCOUNT_NAME']].close()
            del self.names[message['ACCOUNT_NAME']]
            return
        # Иначе отдаём Bad request
        else:
            response = RESPONSE_400
            response['ERROR'] = 'Запрос некорректен.'
            send_message(client, response)
            return

    @log
    def address_message(self, message, names, listen_socks):
        """
        Функция адресной отправки сообщения определённому клиенту. Принимает словарь сообщение,
        список зарегистрированых пользователей и слушающие сокеты. Ничего не возвращает.
        :param message:
        :param names:
        :param listen_socks:
        :return:
        """
        if message['DESTINATION'] in names and names[message['DESTINATION']] in listen_socks:
            send_message(names[message['DESTINATION']], message)
            SERVER_LOGGER.info(f'Отправлено сообщение пользователю {message["DESTINATION"]} '
                               f'от пользователя {message["SENDER"]}.')
        elif message['DESTINATION'] in names and names[message['DESTINATION']] not in listen_socks:
            raise ConnectionError
        else:
            SERVER_LOGGER.error(
                f'Пользователь {message["DESTINATION"]} не зарегистрирован на сервере, '
                f'отправка сообщения невозможна.')

    def main_loop(self):
        """
        Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию
        :return:
        """
        # listen_address, listen_port = get_args()
        #
        # SERVER_LOGGER.info(
        #     f'Запущен сервер, порт для подключений: {listen_port}, \n'
        #     f'адрес с которого принимаются подключения: {listen_address}. \n'
        #     f'Если адрес не указан, принимаются соединения с любых адресов.')
        # Готовим сокет
        # transport = socket(AF_INET, SOCK_STREAM)
        # transport.bind((listen_address, listen_port))
        # transport.settimeout(0.5)

        # список клиентов , очередь сообщений
        # clients = []
        # messages = []

        # Словарь, содержащий имена пользователей и соответствующие им сокеты.
        # names = dict()

        # Слушаем порт
        # transport.listen(8)
        # Основной цикл программы сервера
        self.init_socket()

        while True:
            # Ждём подключения, если таймаут вышел, ловим исключение.
            try:
                client, client_address = self.sock.accept()
            except OSError:
                pass
            else:
                SERVER_LOGGER.info(f'Установлено соедение с ПК {client_address}')
                self.clients.append(client)

            recv_data_lst = []
            send_data_lst = []
            err_lst = []
            # Проверяем на наличие ждущих клиентов
            try:
                if self.clients:
                    recv_data_lst, send_data_lst, err_lst = select.select(self.clients, self.clients, [], 0)
            except OSError:
                pass

            # принимаем сообщения и если ошибка, исключаем клиента.
            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        self.get_client_message(get_message(client_with_message),
                                                self.messages, client_with_message, self.clients, self.names)
                    except Exception:
                        SERVER_LOGGER.info(f'Клиент {client_with_message.getpeername()} '
                                           f'отключился от сервера.')
                        self.clients.remove(client_with_message)

            # Если есть сообщения, обрабатываем каждое.
            for i in self.messages:
                try:
                    self.address_message(i, self.names, send_data_lst)
                except Exception:
                    SERVER_LOGGER.info(f'Связь с клиентом с именем {i["DESTINATION"]} была потеряна')
                    self.clients.remove(self.names[i['DESTINATION']])
                    del self.names[i['DESTINATION']]
            self.messages.clear()


def main():
    # Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию.
    listen_address, listen_port = get_args()

    # Создание экземпляра класса - сервера.
    server = Server(listen_address, listen_port)
    server.main_loop()


if __name__ == '__main__':
    main()

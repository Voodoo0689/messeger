import configparser
import os
import threading
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
from server_database import ServerStorage
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from server_gui import MainWindow, gui_create_model, HistoryWindow, create_stat_model, ConfigWindow
from PyQt5.QtGui import QStandardItemModel, QStandardItem

SERVER_LOGGER = logging.getLogger('server')
new_connection = False
conflag_lock = threading.Lock()

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


class Server(threading.Thread, metaclass=ServerMaker):
    port = Port()

    def __init__(self, listen_address, listen_port, database):
        # Параметры подключения
        self.addr = listen_address
        self.port = listen_port
        # БД сервера
        self.database = database
        # Список подключённых клиентов.
        self.clients = []
        # Список сообщений на отправку.
        self.messages = []
        # Словарь содержащий сопоставленные имена и соответствующие им сокеты.
        self.names = dict()
        super().__init__()

    def init_socket(self):
        SERVER_LOGGER.info(
            f'Запущен сервер, порт для подключений: {self.port}, '
            f'адрес с которого принимаются подключения: {self.addr}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')
        # Готовим сокет
        transport = socket(AF_INET, SOCK_STREAM)
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
            # if message['USER']['ACCOUNT_NAME'] not in self.names.keys():
            #     self.names[message['USER']['ACCOUNT_NAME']] = client
            #     send_message(client, RESPONSE_200)
            if message['USER']['ACCOUNT_NAME'] not in self.names.keys():
                self.names[message['USER']['ACCOUNT_NAME']] = client
                client_ip, client_port = client.getpeername()
                self.database.user_login(message['USER']['ACCOUNT_NAME'], client_ip, client_port)
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
            self.database.user_logout(message['ACCOUNT_NAME'])
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

    def run(self):

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
    # Загрузка файла конфигурации сервера
    config = configparser.ConfigParser()

    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/{'server.ini'}")

    # Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию.
    listen_address, listen_port = get_args()
    # listen_address, listen_port = get_args(
    #     config['SETTINGS']['Default_port'], config['SETTINGS']['Listen_Address'])

    # Инициализация базы данных
    database = ServerStorage(
        os.path.join(
            config['SETTINGS']['Database_path'],
            config['SETTINGS']['Database_file']))
    # Создание экземпляра класса - сервера.
    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    # Создаём графическое окружение для сервера:
    server_app = QApplication(sys.argv)
    main_window = MainWindow()

    # Инициализируем параметры в окна
    main_window.statusBar().showMessage('Server Working')
    main_window.active_clients_table.setModel(gui_create_model(database))
    main_window.active_clients_table.resizeColumnsToContents()
    main_window.active_clients_table.resizeRowsToContents()

    # Функция, обновляющая список подключённых, проверяет флаг подключения, и
    # если надо обновляет список
    def list_update():
        global new_connection
        if new_connection:
            main_window.active_clients_table.setModel(
                gui_create_model(database))
            main_window.active_clients_table.resizeColumnsToContents()
            main_window.active_clients_table.resizeRowsToContents()
            with conflag_lock:
                new_connection = False

    # Функция, создающая окно со статистикой клиентов
    def show_statistics():
        global stat_window
        stat_window = HistoryWindow()
        stat_window.history_table.setModel(create_stat_model(database))
        stat_window.history_table.resizeColumnsToContents()
        stat_window.history_table.resizeRowsToContents()
        stat_window.show()

    # Функция создающяя окно с настройками сервера.
    def server_config():
        global config_window
        # Создаём окно и заносим в него текущие параметры
        config_window = ConfigWindow()
        config_window.db_path.insert(config['SETTINGS']['Database_path'])
        config_window.db_file.insert(config['SETTINGS']['Database_file'])
        config_window.port.insert(config['SETTINGS']['Default_port'])
        config_window.ip.insert(config['SETTINGS']['Listen_Address'])
        config_window.save_btn.clicked.connect(save_server_config)

    # Функция сохранения настроек
    def save_server_config():
        global config_window
        message = QMessageBox()
        config['SETTINGS']['Database_path'] = config_window.db_path.text()
        config['SETTINGS']['Database_file'] = config_window.db_file.text()
        try:
            port = int(config_window.port.text())
        except ValueError:
            message.warning(config_window, 'Ошибка', 'Порт должен быть числом')
        else:
            config['SETTINGS']['Listen_Address'] = config_window.ip.text()
            if 1023 < port < 65536:
                config['SETTINGS']['Default_port'] = str(port)
                print(port)
                with open('server.ini', 'w') as conf:
                    config.write(conf)
                    message.information(
                        config_window, 'OK', 'Настройки успешно сохранены!')
            else:
                message.warning(
                    config_window,
                    'Ошибка',
                    'Порт должен быть от 1024 до 65536')

    # Таймер, обновляющий список клиентов 1 раз в секунду
    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    # Связываем кнопки с процедурами
    main_window.refresh_button.triggered.connect(list_update)
    main_window.show_history_button.triggered.connect(show_statistics)
    main_window.config_btn.triggered.connect(server_config)

    # Запускаем GUI
    server_app.exec_()


if __name__ == '__main__':
    main()

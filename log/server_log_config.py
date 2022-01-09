"""Кофнфиг серверного логгера"""

"""Кофнфиг серверного логгера"""

import sys
import os
import logging
import logging.handlers

sys.path.append('../')
LOGGING_LEVEL = logging.DEBUG
SERVER_FORMATTER = logging.Formatter('%(asctime)s \n%(levelname)s \n%(filename)s \n%(message)s')
PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(PATH, 'server_logs/server.log')
LOG_FILE = logging.handlers.TimedRotatingFileHandler(PATH, encoding='utf8', interval=1, when='D')
LOG_FILE.setFormatter(SERVER_FORMATTER)
LOGGER = logging.getLogger('server')
STREAM_HANDLER = logging.StreamHandler(sys.stderr)
LOGGER.addHandler(STREAM_HANDLER)
LOGGER.addHandler(LOG_FILE)
LOGGER.setLevel(LOGGING_LEVEL)

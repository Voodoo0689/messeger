import sys
import os
import logging

sys.path.append('../')
LOGGING_LEVEL = logging.DEBUG
CLIENT_FORMATTER = logging.Formatter('%(asctime)s %(levelname)s %(filename)s %(message)s')
PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(PATH, 'client_logs/client.log')
LOG_FILE = logging.FileHandler(PATH, encoding='utf8')
LOG_FILE.setFormatter(CLIENT_FORMATTER)
LOGGER = logging.getLogger('client')
LOGGER.addHandler(LOG_FILE)
LOGGER.setLevel(LOGGING_LEVEL)

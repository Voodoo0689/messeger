import sys
import logging
import log.server_log_config
import log.client_log_config
import traceback
import inspect

if sys.argv[0].find('client') == -1:
    LOGGER = logging.getLogger('server')
else:
    LOGGER = logging.getLogger('client')


def log(func_to_log):
    """Функция-декоратор"""

    def log_saver(*args, **kwargs):
        """Обертка"""
        ret = func_to_log(*args, **kwargs)
        LOGGER.debug(f'Была вызвана функция {func_to_log.__name__}\n c параметрами {args}, {kwargs}.'
                     f'Вызов из модуля {func_to_log.__module__}.\n Вызов из'
                     f'функции {traceback.format_stack()[0].strip().split()[-1]}.\n'
                     f' Вызов из функции {inspect.stack()[1][3]}', stacklevel=2)
        return ret

    return log_saver

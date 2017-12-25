import logging
from logging import getLogger

logging.basicConfig(
    format='[{asctime:15}] [{name}.{funcName}:{lineno}] {levelname:7} {message}',
    style='{',
    # level=logging.ERROR,
    # level=logging.DEBUG,
    level=logging.INFO,
)

__all__ = ['getLogger']

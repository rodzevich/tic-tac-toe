import os

from game.logger import getLogger

logger = getLogger(__name__)


class Config(object):
    def __init__(self):
        self.mongodb_uri = self.param('mongodb_uri')
        self.ping_interval = int(self.param('ping_interval', 20))
        self.max_waiting = int(self.param('max_waiting', 10))

    def param(self, name, default=None):
        return os.environ.get(name.upper(), default)

import asyncio
from random import choice

from game.logger import getLogger

logger = getLogger()


class User(object):
    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, User) and self.name == other.name

    def __init__(self, name=None):
        self.name = name
        self.wins = 0
        self.loses = 0
        self.draws = 0
        self.plays = 0
        self.websocket = None
        self.sign = None
        self.room = None

    @classmethod
    async def load_from_db(cls, name, db):
        data = await db.players.find_one({'name': name})

        if data:
            user = cls(name)
            user.wins = data['wins']
            user.loses = data['loses']
            user.draws = data['draws']
            user.plays = data['plays']
            return user

    async def save_to_db(self, db):
        await db.players.update(
            {'name': self.name},
            self.json,
            upsert=True,
        )

    async def send(self, data):
        try:
            await self.websocket.send_json(data)
        except RuntimeError:
            logger.info('Connection with user {} is broken'.format(self.name))

    @property
    def json(self):
        return {
            'name': self.name,
            'sign': self.sign,
            'wins': self.wins,
            'loses': self.loses,
            'draws': self.draws,
            'plays': self.plays,
        }

    def ping(self):
        self.websocket.ping()

    async def disconnect(self):
        logger.info('User %s disconnected', self.name)
        await self.websocket.close()


class AI(User):
    def __init__(self):
        super().__init__(name='AI')

    async def send(self, data):
        action = data.get('action')
        if action == 'turn' and data['active'] == 'you':
            move = self.find_move(data['board'])
            if move:
                x, y = move
                await asyncio.sleep(3)  # emulate hard calculations :)
                await self.room.do_turn(self, x, y)

    def find_move(self, board):
        suitable = []
        for x in range(3):
            for y in range(3):
                if board[x][y] == ' ':
                    suitable.append((x, y))

        return choice(suitable) if suitable else None

    def ping(self):
        pass

    async def save_to_db(self, db):
        pass

    async def disconnect(self):
        pass

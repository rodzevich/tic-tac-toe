import asyncio
from random import choice


class Room(object):
    @classmethod
    async def create(cls, user1, user2, app):
        self = cls()

        self.app = app
        self.turn_number = 0

        self.user1 = user1
        self.user2 = user2
        self.turn = choice((False, True))
        self.board = [[' '] * 3, [' '] * 3, [' '] * 3]  # empty board

        self.active_user.sign = 'X'
        self.waiting_user.sign = 'O'

        self.user1.plays += 1
        self.user2.plays += 1

        self.user1.room = self
        self.user2.room = self

        await self.save_users()
        await self.broadcast_turn()

        return self

    @property
    def active_user(self):
        return self.user1 if self.turn else self.user2

    @property
    def waiting_user(self):
        return self.user2 if self.turn else self.user1

    def another_user(self, user):
        return self.user1 if user == self.user2 else self.user2

    async def save_users(self):
        await asyncio.gather(
            self.user1.save_to_db(self.app['db']),
            self.user2.save_to_db(self.app['db']),
        )

    async def broadcast_turn(self):
        await asyncio.gather(
            self.active_user.send({
                'action': 'turn',
                'active': 'you',
                'board': self.board,
                'you': self.active_user.json,
                'opponent': self.waiting_user.json,
            }),
            self.waiting_user.send({
                'action': 'turn',
                'active': 'opponent',
                'board': self.board,
                'you': self.waiting_user.json,
                'opponent': self.active_user.json,
            }),
        )

    async def finish_game(self, winner):
        if winner:
            winner.wins += 1
            loser = self.another_user(winner)
            loser.loses += 1

            await self.save_users()

            await asyncio.gather(
                winner.send({
                    'action': 'game_finished',
                    'winner': 'you',
                    'board': self.board,
                }),
                loser.send({
                    'action': 'game_finished',
                    'winner': 'opponent',
                    'board': self.board,
                }),
            )
        else:
            self.user1.draws += 1
            self.user2.draws += 1

            await self.save_users()

            msg = {
                'action': 'game_finished',
                'winner': 'nobody',
                'board': self.board,
            }
            await asyncio.gather(self.user1.send(msg), self.user2.send(msg))

        await self.close()

    def check_winner(self, x, y):
        b = self.board
        if len(set(b[x])) == 1:  # vertical
            return True
        if len(set(b[i][y] for i in range(3))) == 1:  # horizontal
            return True
        if x == y:  # diagonal
            if b[0][0] == b[1][1] == b[2][2]:
                return True
        if 2 - x == y:  # diagonal
            if b[0][2] == b[1][1] == b[2][0]:
                return True
        return False

    async def do_turn(self, user, x, y):
        if user == self.waiting_user:
            return await user.send({'error': 'Not your turn'})

        if self.board[x][y] == ' ':
            self.board[x][y] = user.sign
        else:
            return await user.send({'error': 'Cell is already occupied'})

        self.turn_number += 1

        if self.check_winner(x, y):
            await self.finish_game(winner=user)
        elif self.turn_number >= 9:  # board is filled up
            await self.finish_game(winner=None)
        else:
            self.turn = not self.turn
            await self.broadcast_turn()

    async def user_disconnected(self, user):
        opponent = self.another_user(user)
        await self.finish_game(winner=opponent)

    async def close(self):
        self.app['online'].discard(self.user1)
        self.app['online'].discard(self.user2)
        self.app['rooms'].discard(self)

        await asyncio.gather(self.user1.disconnect(), self.user2.disconnect())

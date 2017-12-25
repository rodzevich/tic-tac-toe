#!/usr/local/bin/python3.6
import asyncio
import json
import os
import random
import sys

import aiohttp
from aiohttp import WSMsgType
from aiohttp.client_exceptions import WSServerHandshakeError

from logger import getLogger

logger = getLogger(__name__)


class Client(object):
    QUEUED = 0
    MY_TURN = 1
    OPPONENTS_TURN = 2

    def __init__(self):
        self.host = os.environ.get('HOST', '127.0.0.1:8080')
        self.api_url = 'ws://{}/v1'.format(self.host)
        self.state = Client.QUEUED

    async def main(self):
        self.session = aiohttp.ClientSession()

        name = input('Enter your name or hit Enter for random one: ')
        if not name:
            name = random.choice(('John', 'Smith', 'Bob', 'Miller', 'Scott', 'Allen', 'Tom', 'Wilson'))

        try:
            url = '{}/ws/?name={}'.format(self.api_url, name)
            async with self.session.ws_connect(url) as ws:
                self.websocket = ws

                async for msg in ws:
                    logger.debug('MSG: %s', msg)
                    if msg.tp == WSMsgType.text:
                        if msg.data == 'close':
                            logger.info('Server closed connection')
                            await ws.close()
                        else:
                            await self.process_request(msg.data)
                    elif msg.tp == WSMsgType.error:
                        logger.exception('Got ws error %s', id(ws))
        except WSServerHandshakeError:
            # Unfortunately, aiohttp doesn't provide response body on error
            print('Unable to connect')
        finally:
            self.shutdown()

    async def process_request(self, data):
        try:
            data = json.loads(data)
        except json.decoder.JSONDecodeError:
            return

        if not isinstance(data, dict):
            return

        logger.debug('Got request: %s', data)

        error = data.get('error')
        if error:
            print(error)
            return

        print()
        action = data.get('action')
        if action == 'queued':
            print('Please wait for other player')
        elif action == 'board':
            u = data['you']
            print('You: {}({}) wins:{} loses:{} draws:{} plays:{}'.format(
                u['name'], u['sign'], u['wins'], u['loses'], u['draws'], u['plays']))
            u = data['opponent']
            print('Opponent: {}({}) wins:{} loses:{} draws:{} plays:{}'.format(
                  u['name'], u['sign'], u['wins'], u['loses'], u['draws'], u['plays']))

            self.draw_board(data.get('board'))

            if data['turn'] == 'you':
                self.state = Client.MY_TURN
                print('Your turn...')
            else:
                self.state = Client.OPPONENTS_TURN
                print('Opponent is thinking...')
        elif action == 'game_finished':
            self.draw_board(data['board'])

            if data['winner'] == 'you':
                print('You won!')
            elif data['winner'] == 'opponent':
                print('You lose!')
            else:
                print('Draw!')

            self.websocket.close()
            quit()

    def draw_board(self, board):
        board = list(zip(*board))  # transpose board
        print('  0   1   2')
        print('0', ' │ '.join(board[0]))
        print(' ───┼───┼───')
        print('1', ' │ '.join(board[1]))
        print(' ───┼───┼───')
        print('2', ' │ '.join(board[2]))

    def stdin(self):
        data = sys.stdin.readline().rstrip()
        if self.state == Client.MY_TURN:
            try:
                x, y = map(int, data.split())
            except ValueError:
                print('Type X and Y e.g. 0 1')
                return

            if x < 0 or x > 2 or y < 0 or y > 2:
                print('X and Y must be 0..2')
                return

            self.websocket.send_str(json.dumps({
                'action': 'turn',
                'args': [x, y],
            }))
        else:
            return  # Ignore input

    def shutdown(self):
        self.session.close()


if __name__ == '__main__':
    client = Client()

    try:
        loop = asyncio.get_event_loop()
        loop.add_reader(sys.stdin, client.stdin)
        loop.run_until_complete(client.main())
        loop.close()
    except KeyboardInterrupt:
        pass

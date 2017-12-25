import asyncio
import json

from aiohttp import WSMsgType, web
from aiohttp.web import WebSocketResponse

from game.logger import getLogger
from game.models.room import Room
from game.models.user import AI, User

logger = getLogger(__name__)


class WebSocketHandler(web.View):
    async def get(self):
        app = self.request.app

        try:
            name = self.request.query['name']
        except KeyError:
            return self.response_error('Name is required')

        user = await User.load_from_db(name, app['db'])
        if not user:
            user = User(name)
            await user.save_to_db(app['db'])

        if user in app['online']:
            return self.response_error('User is already online')

        ws = WebSocketResponse(compress=True)
        await ws.prepare(self.request)

        user.websocket = ws

        await self.user_connected(user, app)

        await self.user_message_loop(user, app)

        return ws

    async def user_connected(self, user, app):
        app['online'].add(user)
        logger.info('User {} connected'.format(user.name))

        if app['waiting']:
            app['ai_task'].cancel()

            user2 = app['waiting']
            app['waiting'] = None

            room = await Room.create(user, user2, app)
            app['rooms'].add(room)

            logger.info('Game between {} and {} has started'.format(
                        user.name, user2.name))
        else:
            app['waiting'] = user
            await user.websocket.send_json({'action': 'queued'})

            app['ai_task'] = asyncio.ensure_future(self.run_ai_game(app))

    async def user_message_loop(self, user, app):
        async for msg in user.websocket:
            logger.debug('MSG: %s', msg)
            if msg.tp == WSMsgType.text:
                if msg.data == 'close':
                    logger.info('Close ws connection')
                    await user.websocket.close()
                else:
                    try:
                        data = json.loads(msg.data)
                    except json.decoder.JSONDecodeError:
                        logger.error('Invalid JSON request: %s', msg.data)
                    else:
                        logger.info('Got request: %s', data)
                        await self.process_request(user, data, app)
            elif msg.tp == WSMsgType.error:
                logger.exception('Got ws error %s', id(user.websocket))

    def response_error(self, message):
        return web.json_response({'error': message}, status=400)

    async def process_request(self, user, data, app):
        if not isinstance(data, dict) or 'action' not in data or 'args' not in data:
            return await user.send({'error': 'Action and args required'})

        act = data['action']
        args = data['args']
        if act == 'turn':
            try:
                x, y = int(args[0]), int(args[1])
                assert 0 <= x <= 2
                assert 0 <= y <= 2
            except (IndexError, ValueError, AssertionError):
                return await user.send({'error': 'Invalid turn args'})
            await user.room.do_turn(user, x, y)

    async def run_ai_game(self, app):
        await asyncio.sleep(app['config'].max_waiting)

        user = app['waiting']
        app['waiting'] = None

        room = await Room.create(user, AI(), app)
        app['rooms'].add(room)

        logger.info('Game between AI and {} has started'.format(user.name))

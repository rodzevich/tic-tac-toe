import asyncio

from aiohttp import web
from motor.motor_asyncio import AsyncIOMotorClient

from game.config import Config
from game.logger import getLogger
from game.views import WebSocketHandler

logger = getLogger(__name__)


def create_app():
    app = web.Application()
    app.router.add_route('GET', '/v1/ws/', WebSocketHandler,
                         expect_handler=web.Request.json)
    return app


async def on_start(app):
    config = Config()

    client = AsyncIOMotorClient(config.mongodb_uri)
    app['db_client'] = client
    app['db'] = client.get_default_database()  # defined in mongodb_uri
    app['config'] = config

    app['ping_task'] = asyncio.ensure_future(ping(app))

    app['online'] = set()
    app['rooms'] = set()
    app['waiting'] = None  # slot for waiting user

    await app['db'].users.create_index('name', unique=True)


async def ping(app):
    while True:
        await asyncio.sleep(app['config'].ping_interval)

        online = app['online']
        for user in online.copy():
            if user not in online:  # already removed
                continue

            try:
                logger.info('Ping user %s', user.name)
                user.ping()
            except RuntimeError:
                if user.room:
                    await user.room.user_disconnected(user)
                else:
                    online.discard(user)

                    await user.disconnect()
                    if app['waiting'] == user:
                        app['ai_task'].cancel()
                        app['waiting'] = None


async def on_shutdown(app):
    app['ping_task'].cancel()
    await app['ping_task']

    for user in app['online']:
        await user.disconnect()

    app['db_client'].close()
    await app['db_client'].wait_closed()


app = create_app()
app.on_startup.append(on_start)
app.on_shutdown.append(on_shutdown)

"""
This module implements the :class:`~Server` class, responsible for creating
tunneling servers.
"""

import logging
import asyncio
from urllib import parse
import os

import websockets
from aiohttp import web
import aiohttp_jinja2
import jinja2

from .connection import Connection, TunnelListenError
from . import ids


logger = logging.getLogger(__name__)


class HealthCheck:
    here = os.path.abspath(os.path.dirname(__file__))
    template_dir = os.path.join(here, 'templates')

    def __init__(self, server, app):
        self.server = server
        self.app = app

        self.create_routes()
        aiohttp_jinja2.setup(
            self.app,
            loader=jinja2.FileSystemLoader(self.template_dir))

    def create_routes(self):
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/close/{connid}', self.close)

    @aiohttp_jinja2.template('index.html.j2')
    def index(self, request):
        return {'server': self.server}

    async def close(self, request):
        id = int(request.match_info['connid'])
        conn = self.server.connections[id]
        conn.ws_close()
        await conn.wait_closed()
        return web.Response(text='OK')


class Server:
    """
    The Server class represents the tunnel server listening on ``host:port``.
    """

    def __init__(
        self, host, port,
        response_timeout=5, heartbeat_interval=10,
        healthcheck_port=9001, loop=None
    ):
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self.host, self.port = host, port
        self.response_timeout = response_timeout
        self.heartbeat_interval = heartbeat_interval
        self.healthcheck_port = healthcheck_port
        self._task = None
        self._task_cancelled = False
        self.listening = self.loop.create_future()
        self.connections = ids.Ids()

    def start(self):
        """
        Start the server. This function is not a coroutine, will not block.
        """
        self._task = asyncio.ensure_future(self.task())

    async def handle(self, ws, path):
        path = parse.unquote(path)
        logger.info('connection from {} {}'.format(ws.remote_address, path))
        try:
            [mode, host, port] = [part for part in path.split('/') if part]
            port = int(port)
        except:
            logger.error('invalid path: {}'.format(path))
        else:
            conn = Connection(
                mode, host, port, ws,
                self.response_timeout, self.heartbeat_interval
            )
            conn_id = self.connections.store(conn)  # TODO no slots
            conn.id = conn_id
            try:
                await conn.handle()
            except TunnelListenError as exc:
                logger.error(exc)
        finally:
            logger.info('connection closed {}'.format(ws.remote_address))
            del self.connections[conn_id]

    async def task(self):
        ws_server = None
        health_server = None
        try:
            try:
                ws_server = await websockets.serve(
                    self.handle,
                    self.host,
                    self.port,
                    loop=self.loop
                )
                # the health check service
                app = web.Application(loop=self.loop)
                HealthCheck(self, app)
                health_server = await self.loop.create_server(
                    app.make_handler(), self.host, self.healthcheck_port
                )
            except asyncio.CancelledError:
                raise
            except OSError as exc:
                msg = 'can not listen on {}:{} ({})'
                logger.error(msg.format(self.host, self.port, exc))
                return

            self.listening.set_result(None)
            msg = 'tunnel listening on {}:{}'
            logger.info(msg.format(self.host, self.port))
            await self.loop.create_future()
        except asyncio.CancelledError:
            if ws_server:
                ws_server.close()
                await ws_server.wait_closed()  # this will cancel the handler
            if health_server:
                health_server.close()
                await health_server.wait_closed()

        # try:
        #     ws_server = await websockets.serve(
        #         self.handle, self.host, self.port, loop=self.loop
        #     )
        # except asyncio.CancelledError:
        #     return
        # except OSError as exc:
        #     msg = 'can not listen on {}:{} ({})'
        #     logger.error(msg.format(self.host, self.port, exc))
        #     return
        # except Exception:
        #     msg = 'can not listen on {}:{}'
        #     logger.exception(msg.format(self.host, self.port))
        #     return
        # else:
        #     self.listening.set_result(None)
        #     msg = 'tunnel listening on {}:{}'
        #     logger.info(msg.format(self.host, self.port))
        #
        # try:
        #     await self.loop.create_future()
        # except asyncio.CancelledError:
        #     ws_server.close()
        #     await ws_server.wait_closed()  # this will cancel the handler

    async def close(self):
        if not self._task:
            return
        if not self._task_cancelled:
            self._task_cancelled = True
            self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        logger.info('bye...')

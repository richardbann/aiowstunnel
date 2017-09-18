"""
This module implements the :class:`~Server` class, responsible for creating
tunneling servers.
"""

import logging
import asyncio
from urllib import parse

import websockets

from .connection import Connection, TunnelListenError


logger = logging.getLogger(__name__)


class Server:
    """
    The Server class represents the tunnel server listening on ``host:port``.
    """

    def __init__(
        self, host, port,
        response_timeout=5, heartbeat_interval=10,
        loop=None
    ):
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self.host, self.port = host, port
        self.response_timeout = response_timeout
        self.heartbeat_interval = heartbeat_interval
        self._task = None
        self._task_cancelled = False
        self.listening = self.loop.create_future()

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
            try:
                await conn.handle()
            except TunnelListenError as exc:
                logger.error(exc)
        finally:
            logger.info('connection closed {}'.format(ws.remote_address))

    async def task(self):
        try:
            ws_server = await websockets.serve(
                self.handle, self.host, self.port, loop=self.loop
            )
        except asyncio.CancelledError:
            return
        except OSError as exc:
            msg = 'can not listen on {}:{} ({})'
            logger.error(msg.format(self.host, self.port, exc))
            return
        except Exception:
            msg = 'can not listen on {}:{}'
            logger.exception(msg.format(self.host, self.port))
            return
        else:
            self.listening.set_result(None)
            msg = 'tunnel listening on {}:{}'
            logger.info(msg.format(self.host, self.port))

        try:
            await self.loop.create_future()
        except asyncio.CancelledError:
            ws_server.close()
            await ws_server.wait_closed()  # this will cancel the handler

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

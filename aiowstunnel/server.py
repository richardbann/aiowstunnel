"""
This module implements the :class:`~Server` class, responsible for creating
tunneling servers.
"""

import logging
import asyncio
from urllib import parse
import json
from http import HTTPStatus

import websockets

from .connection import Connection, TunnelListenError
from . import ids


logger = logging.getLogger(__name__)


# class Protocol(websockets.WebSocketServerProtocol):
#     async def process_request(self, path, request_headers):
#         if path == '/stats/json':
#             logger.debug('.......... {}'.format(path))
#             return HTTPStatus.OK, [], b'OK'


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
        self.connections = ids.Ids()

    def start(self):
        """
        Start the server. This function is not a coroutine, will not block.
        """
        self._task = asyncio.ensure_future(self.task())

    @property
    def stats(self):
        fmt = '%Y-%m-%d %H:%M:%S'
        return {
            'host': self.host,
            'port': self.port,
            'connections': [{
                'id': id,
                'mode': conn.mode,
                'host': conn.host,
                'port': conn.port,
                'createTime': conn.create_time.strftime(fmt),
                'connections': [{
                    'id': id,
                    'addr': fwdconn.peername[0],
                    'port': fwdconn.peername[1],
                    'fromSocket': fwdconn.from_socket,
                    'toSocket': fwdconn.to_socket,
                    'createTime': fwdconn.create_time.strftime(fmt)
                } for id, fwdconn in conn.connections.items()]
            } for id, conn in self.connections.items()]
        }

    async def handle(self, ws, path):
        addr = ws.remote_address
        logger.info('connection from {} {}'.format(addr, path))
        path = parse.unquote(path)
        if path == '/stats':
            while True:
                try:
                    await ws.send(json.dumps(self.stats))
                    await asyncio.sleep(1)
                except:
                    logger.info('connection closed {}'.format(addr))
                    return
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
            logger.info('connection closed {}'.format(addr))
            del self.connections[conn_id]

    async def task(self):
        class Protocol(websockets.WebSocketServerProtocol):
            async def process_request(inner_self, path, request_headers):
                try:
                    if path == '/stats/json':
                        stats = json.dumps(self.stats)
                        body = bytes(stats, 'utf-8')
                        return HTTPStatus.OK, [], body
                except:
                    logger.exception('exc:')

        ws_server = None
        try:
            try:
                ws_server = await websockets.serve(
                    self.handle,
                    self.host,
                    self.port,
                    loop=self.loop,
                    create_protocol=Protocol
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

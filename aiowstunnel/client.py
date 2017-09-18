import asyncio
import logging

import websockets

from .connection import Connection
from . import LISTEN, CONNECT


logger = logging.getLogger(__name__)


class Client:
    def __init__(
        self, server_mode,
        tunnel_host, tunnel_port,
        listen_host, listen_port,
        connect_host, connect_port,
        ssl=None,
        initial_delay=1, delay_factor=1.2, max_delay=10,
        response_timeout=5, heartbeat_interval=10
    ):
        assert server_mode in (LISTEN, CONNECT)

        self.server_mode = server_mode
        self.tunnel_host, self.tunnel_port = tunnel_host, tunnel_port
        self.listen_host, self.listen_port = listen_host, listen_port
        self.ssl = ssl

        self.mode = LISTEN if server_mode == CONNECT else CONNECT
        if server_mode == LISTEN:
            self.fwd_host, self.fwd_port = listen_host, listen_port
            self.conn_host, self.conn_port = connect_host, connect_port
        else:
            self.fwd_host, self.fwd_port = connect_host, connect_port
            self.conn_host, self.conn_port = listen_host, listen_port
        self.url = '{}://{}:{}/{}/{}/{}'.format(
            'wss' if ssl else 'ws',
            tunnel_host, tunnel_port, server_mode, self.fwd_host, self.fwd_port
        )

        self.initial_delay = initial_delay
        self.delay_factor = delay_factor
        self.max_delay = max_delay
        self.response_timeout = response_timeout
        self.heartbeat_interval = heartbeat_interval

        self._task = None
        self._task_cancelled = False

    def intervals(self):
        d = self.initial_delay
        while True:
            yield d
            d *= self.delay_factor
            d = min(d, self.max_delay)

    def start(self):
        self._task = asyncio.ensure_future(self.task())

    async def safe_close(self, ws):
        try:
            await ws.close()
        except:
            pass

    async def try_connect(self):
        # do not raise or raise CancelledError to stop,
        # raise stg else to retry
        ws = await websockets.connect(self.url, ssl=self.ssl)
        logger.info('connected to {}'.format(self.url))
        conn = Connection(
            self.mode,
            self.conn_host, self.conn_port,
            ws, self.response_timeout, self.heartbeat_interval
        )
        try:
            await conn.handle()
        except:
            await self.safe_close(ws)
            raise
        await self.safe_close(ws)

    async def wait_loop(self):
        for waitsec in self.intervals():
            try:
                await self.try_connect()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                msg = 'connection to {} failed ({}), waiting {:.2f} seconds'
                logger.error(msg.format(self.url, exc, waitsec))
                try:
                    await asyncio.sleep(waitsec)
                except asyncio.CancelledError:
                    break
            else:
                break

    async def task(self):
        while not self._task_cancelled:
            await self.wait_loop()
        logger.info('connection closed')

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

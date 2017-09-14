import logging
from asyncio import ensure_future, CancelledError, sleep

import websockets

from . import LISTEN, CONNECT
from . import packets


logger = logging.getLogger(__name__)


class TunnelRejectedError(Exception):
    pass


class Client:
    def __init__(self, host, port, mode, fwd_host, fwd_port, ssl=None):
        assert mode in (LISTEN, CONNECT)
        self.url = '{}://{}:{}/{}/{}/{}'.format(
            'wss' if ssl else 'ws',
            host, port, mode, fwd_host, fwd_port
        )
        self.ssl = ssl
        self.initial_delay = 1
        self.delay_factor = 1.2
        self.max_delay = 10

        self._task = None
        self._closed = False

    def start(self):
        self._task = ensure_future(self.task())

    def intervals(self):
        d = self.initial_delay
        while True:
            yield d
            d *= self.delay_factor
            d = min(d, self.max_delay)

    async def handle(self):
        while True:
            try:
                packet = packets.get_packet(await self.ws.recv())
                logger.debug('packet: {}'.format(packet))
            except (CancelledError, websockets.ConnectionClosed):
                break
            except Exception:
                logger.exception('unexpected exception in client handle')
                break
        await self.ws.close()

    async def wait_loop(self):
        for waitsec in self.intervals():
            try:
                ws = await websockets.connect(self.url, ssl=self.ssl)
                packet = packets.get_packet(await ws.recv())
                if packet.name == 'OK':
                    logger.info('tunnel accepted')
                else:
                    raise TunnelRejectedError()
            except CancelledError:
                raise
            except (
                websockets.exceptions.InvalidStatusCode,
                ConnectionError,
                websockets.ConnectionClosed
            ):
                msg = 'connection to {} failed, waiting {:.2f} seconds'
                logger.warning(msg.format(self.url, waitsec))
            except TunnelRejectedError:
                msg = 'tunnel {} rejected, waiting {:.2f} seconds'
                logger.warning(msg.format(self.url, waitsec))
            except Exception:
                msg = 'connection to {} failed, waiting {:.2f} seconds'
                logger.exception(msg.format(self.url, waitsec))
            else:
                return ws

            await sleep(waitsec)

    async def task(self):
        while not self._closed:
            try:
                self.ws = await self.wait_loop()
            except CancelledError:
                return
            await self.handle()

    def close(self):
        self._closed = True
        if self._task:
            self._task.cancel()

    async def wait_closed(self):
        if self._task:
            await self._task

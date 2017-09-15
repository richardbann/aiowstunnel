import logging
import asyncio

from . import packets

logger = logging.getLogger(__name__)


class FwdConnection:
    def __init__(self, r, w, connection):
        self.r, self.w, self.connection = r, w, connection
        self.peername = self.w.get_extra_info('peername')

        self.id = None
        self.peer_id = None
        self.response = connection.ws.loop.create_future()
        self.done = connection.ws.loop.create_future()
        self.close_response = connection.ws.loop.create_future()
        self._closed = False
        self.write_task = None
        self.write_queue = asyncio.Queue()

    def closed(self):
        self.close_nowait()
        if not self.close_response.done():
            self.close_response.set_result(True)

    def accept(self, peer_id):
        self.peer_id = peer_id
        if not self.response.done():
            self.response.set_result(True)

    def reject(self):
        if not self.response.done():
            self.response.set_result(False)

    def data(self, d):
        self.write_queue.put_nowait(d)

    async def _write_loop(self):
        while not self._closed:
            try:
                data = await self.write_queue.get()
                self.w.write(data)
                await self.w.drain()
            except:
                break

    async def _request_tunnel(self):
        await self.connection.send_safe(packets.Request(self.id))
        try:
            # close will call reject to set result on self.response
            resp = await asyncio.wait_for(self.response, 5)  # TODO config
            if not resp:
                self.close_nowait()
        except asyncio.TimeoutError:
            logger.error('response timeout')
            self.connection.ws_close()

    async def _read_loop(self):
        while True:
            try:
                data = await self.r.read(8192)
            except:
                data = None
            if not data:
                break
            if self.peer_id is not None:
                pack = packets.Data(self.peer_id, data)
                await self.connection.send_safe(pack)

    async def handle(self):
        # will not be cancelled
        if (self.id is None) or self._closed:
            return
        # connection from the listener, request, wait for response
        if self.peer_id is None:
            msg = 'tunneling server connection from {}'
            logger.info(msg.format(self.peername))
            await self._request_tunnel()

        if not self._closed:
            self.write_task = asyncio.ensure_future(self._write_loop())
            await self._read_loop()

        # closing
        self.close_nowait()
        if self.peer_id is not None:
            await self.connection.send_safe(packets.Closed(self.peer_id))
        # await self.close_response
        try:
            await asyncio.wait_for(self.close_response, 5)
        except asyncio.TimeoutError:
            self.connection.ws_close()

        self.done.set_result(True)

    def close_nowait(self):
        self._closed = True
        self.w.close()
        self.reject()  # will set response future

    async def close(self):
        self.closed()  # will set close_response future
        if self.write_task:
            self.write_task.cancel()
            await self.write_task
        await self.done

import logging
import asyncio

import websockets

from . import packets

logger = logging.getLogger(__name__)


class FwdConnection:
    def __init__(self, r, w, ws):
        self.r, self.w, self.ws = r, w, ws
        self.peername = self.w.get_extra_info('peername')

        self.id = None
        self.peer_id = None
        self.response = ws.loop.create_future()
        self.done = ws.loop.create_future()
        self._closed = False
        self.write_task = None

    def accept(self, peer_id):
        self.peer_id = peer_id
        if not self.response.done():
            self.response.set_result(True)

    def reject(self):
        if not self.response.done():
            self.response.set_result(False)

    async def write_loop(self):
        while not self._closed:
            try:
                data = await self.write_queue.get()
                self.w.write(data)
                await self.w.drain()
            except:
                break

    async def handle(self):
        # will not be cancelled
        if (self.id is None) or self._closed:
            return
        # connection from the listener, request, wait for response
        if self.peer_id is None:
            msg = 'tunneling server connection from {}'
            logger.info(msg.format(self.peername))
            try:  # we need to request
                await self.ws.send(packets.Request(self.id).as_bytes)
                # close will call reject to set result on self.response
                resp = await asyncio.wait_for(self.response, 5)  # TODO config
                if not resp:
                    self.close_nowait()
            except websockets.ConnectionClosed:
                pass
            except asyncio.TimeoutError:
                logger.error('response timeout')
                await self.ws.close()

        if not self._closed:
            self.write_task = asyncio.ensure_future(self.write_loop())
            # the read loop
            while True:
                try:
                    data = await self.r.read(8192)
                except:
                    data = None
                if not data:
                    break
                if self.peer_id:
                    try:
                        pack = packets.Data(self.peer_id, data).as_bytes
                        await self.ws.send(pack)
                    except:
                        pass

        self.done.set_result(True)

    def close_nowait(self):
        self._closed = True
        self.w.close()
        self.reject()

    async def close(self):
        self.close_nowait()
        if self.write_task:
            self.write_task.cancel()
            await self.write_task
        await self.done

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
        self.sent_cnt = 0  # data packets sent after sending a continue
        self.recv_cnt = 0  # data packets received after last continue
        self.queue_ok = None

    def closed(self):
        self.close_nowait()
        if not self.close_response.done():
            self.close_response.set_result(None)

    def accept(self, peer_id):
        self.peer_id = peer_id
        if not self.response.done():
            self.response.set_result(True)

    def reject(self):
        if not self.response.done():
            self.response.set_result(False)

    def data(self, d):
        if self.recv_cnt == 10:  # TODO: configure
            self.connection.ws_close()
        else:
            self.recv_cnt += 1
            self.write_queue.put_nowait(d)

    def got_continue(self):
        self.recv_cnt = 0

    async def _write_loop(self):
        while not self._closed:
            try:
                data = await self.write_queue.get()
                self.w.write(data)
                await self.w.drain()
                if self.write_queue.qsize() <= 5:  # TODO: configure
                    if self.queue_ok and not self.queue_ok.done():
                        self.queue_ok.set_result(None)
            except:
                break

    async def _request_tunnel(self):
        await self.connection.send_safe(packets.Request(self.id))
        try:
            # close will call reject to set result on self.response
            resp = await asyncio.wait_for(self.response, 5)
            if not resp:
                self.close_nowait()
        except asyncio.TimeoutError:
            logger.error('response timeout')
            self.connection.ws_close()

    async def _read_loop(self):
        while True:
            if self.sent_cnt == 10:  # TODO: configure
                # TODO: configure
                if self.write_queue.qsize() > 10 and not self._closed:
                    # wait for the write_queue to shrink below limit
                    self.queue_ok = self.connection.ws.loop.create_future()
                    await self.queue_ok  # TODO: set result in case of close
                    self.queue_ok = None
                pack = packets.Continue(self.peer_id)
                await self.connection.send_safe(pack)
                self.sent_cnt = 0
            try:
                data = await self.r.read(8192)
            except:
                data = None
            if not data:
                break

            pack = packets.Data(self.peer_id, data)
            self.sent_cnt += 1
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

        if not self._closed and self.peer_id is not None:
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

        self.done.set_result(None)

    def close_nowait(self):
        self._closed = True
        self.w.close()
        self.reject()  # will set response future
        if self.queue_ok and not self.queue_ok.done():
            self.queue_ok.set_result(None)

    async def close(self):
        self.closed()  # will set close_response future
        if self.write_task:
            self.write_task.cancel()
            await self.write_task
        await self.done

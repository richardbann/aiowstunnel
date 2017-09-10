import logging
from asyncio import (
    ensure_future, CancelledError, wait, start_server, Queue, wait_for,
    TimeoutError
)
from urllib.parse import unquote
import functools

import websockets

from . import LISTEN, CONNECT
from .ids import Ids, IdException
from . import packets


logger = logging.getLogger(__name__)


class FwdConnection:
    def __init__(self, r, w, ws):
        self.r, self.w, self.ws = r, w, ws
        self.id = None
        self.peer_id = None
        self.response = ws.loop.create_future()
        self.done = ws.loop.create_future()
        self.write_task = None
        self.write_queue = Queue()
        self.peername = self.w.get_extra_info('peername')
        self._closed = False

    def accept(self, peer_id):
        self.peer_id = peer_id
        self.response.set_result(True)

    def reject(self):
        self.response.set_result(False)

    def data(self, data):
        self.write_queue.put_nowait(data)

    async def write_loop(self):
        while not self._closed:
            try:
                data = await self.write_queue.get()
                self.w.write(data)
                await self.w.drain()
            except CancelledError:
                break
            except Exception:
                break

    async def handle(self):
        if self.id is None:
            return
        if self.peer_id is None:
            logger.info('tunneling connection from {}'.format(self.peername))
            try:  # we need to request
                await self.ws.send(packets.Request(self.id).as_bytes)
                await wait_for(self.response, 5)  # TODO config timeout ?
            except CancelledError:
                self.close()
            except TimeoutError:
                logger.error('response timeout')
                await self.ws.close()

        if not self._closed:
            self.write_task = ensure_future(self.write_loop())

        while True:
            try:
                data = await self.r.read(8192)
            except (CancelledError, ConnectionError):
                data = None
            if not data:
                break
            if self.peer_id:
                try:
                    pack = packets.Data(self.peer_id, data).as_bytes
                    await self.ws.send(pack)
                except (CancelledError, ConnectionError):
                    pass

        self.done.set_result(True)

    def close(self):
        logger.debug(self.write_task)
        self._closed = True
        self.w.close()
        if self.write_task is not None:
            self.write_task.cancel()

    async def wait_closed(self):
        await self.done
        if self.write_task:
            await self.write_task


class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port

        self._wsserver = None
        self._task = None
        self.connections = Ids()

    def start(self):
        self._task = ensure_future(self.task())

    async def task(self):
        try:
            self._wsserver = await websockets.serve(
                self.handle, self.host, self.port
            )
        except CancelledError:
            pass
        except OSError as exc:
            msg = 'can not listen on {}:{} ({})'
            logger.warning(msg.format(self.host, self.port, exc))
        except Exception:
            msg = 'can not listen on {}:{}'
            logger.exception(msg.format(self.host, self.port))
        else:
            msg = 'tunnel listening on {}:{}'
            logger.info(msg.format(self.host, self.port))

    async def listen_handler(self, r, w, ws):
        fwd_conn = FwdConnection(r, w, ws)
        try:
            fwd_conn.id = self.connections.store(fwd_conn)
        except IdException:
            pass
        await fwd_conn.handle()
        del self.connections[fwd_conn.id]

    async def send(self, ws, data):
        try:
            await ws.send(data)
        except websockets.ConnectionClosed:
            pass

    async def handle_listen(self, host, port, ws):
        try:
            fwd_server = await start_server(
                functools.partial(self.listen_handler, ws=ws),
                host=host, port=port,
                loop=ws.loop
            )
        except CancelledError:
            raise
        except Exception as exc:
            msg = 'can not listen on {}:{} ({})'
            logger.error(msg.format(host, port, exc))
            await self.send(ws, packets.Error().as_bytes)
            return
        else:
            await self.send(ws, packets.OK().as_bytes)
            logger.info('fwd server {}:{} listening'.format(host, port))

        while True:
            try:
                packet = packets.get_packet(await ws.recv())
                logger.debug('packet: {}'.format(packet))
            except (CancelledError, websockets.ConnectionClosed):
                break
            except Exception:
                logger.exception('unexpected exception in server handle')
                break

        [c.close() for c in self.connections.values()]
        if self.connections:
            conns = self.connections.values()
            await wait([c.wait_closed() for c in conns])
        fwd_server.close()
        await fwd_server.wait_closed()
        logger.info('fwd server {}:{} closed'.format(host, port))

    async def handle(self, ws, _path):
        path = unquote(_path)
        logger.info('connection from {} {}'.format(ws.remote_address, path))
        try:
            [mode, host, port] = [part for part in path.split('/') if part]
            port = int(port)
        except:
            logger.error('invalid path: {}'.format(path))
        else:
            if mode == LISTEN:
                await self.handle_listen(host, port, ws)
            elif mode == CONNECT:
                pass
        finally:
            logger.info('connection closed {}'.format(ws.remote_address))

    def close(self):
        if self._task:
            self._task.cancel()
        if self._wsserver:
            self._wsserver.close()

    async def wait_closed(self):
        if self._task:
            await self._task
        if self._wsserver:
            self._wsserver.wait_closed()
        logger.info('tunnel closed on {}:{}'.format(self.host, self.port))

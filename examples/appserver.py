import asyncio
import signal
import logging


root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
fmt = logging.Formatter(
    'APPSRV|%(asctime)s|%(levelname)s|%(name)s|%(message)s|'
)
stream_handler.setFormatter(fmt)
stream_handler.addFilter(logging.Filter('aiowstunnel'))
root_logger.addHandler(stream_handler)
logger = logging.getLogger('aiowstunnel.appserver')


class Server:
    def __init__(self, host, port):
        self.host, self.port = host, port
        self.hostport = '{}:{}'.format(host, port)
        self._connections = set()
        self._task = None
        self._stop = asyncio.get_event_loop().create_future()

    async def handle_conn(self, r, w):
        addr = w.get_extra_info('peername')
        logger.info('connection open {}'.format(addr))
        while True:
            try:
                data = await r.readline()
                if not data:
                    break
                if data == b'q\r\n':
                    w.close()
                else:
                    w.write(data)
                    await w.drain()
            except ConnectionError:
                break
        logger.info('connection close {}'.format(addr))

    async def handle(self, r, w):
        conn_task = asyncio.ensure_future(self.handle_conn(r, w))
        conn = (w, conn_task)
        self._connections.add(conn)
        await conn_task
        self._connections.remove(conn)

    async def task(self):
        try:
            srv = await asyncio.start_server(self.handle, self.host, self.port)
        except OSError:
            logger.error('can not listen on {}'.format(self.hostport))
            return

        logger.info('listening on {}'.format(self.hostport))
        await self._stop

        srv.close()
        await srv.wait_closed()
        connections = list(self._connections)
        if connections:
            [w.close() for w, _ in connections]
            await asyncio.wait([t for _, t in connections])
        logger.info('bye...')

    def start(self):
        self._task = asyncio.ensure_future(self.task())

    async def close(self):
        if not self._stop.done():
            self._stop.set_result(None)
        await self._task


async def serve(stop):
    srv1 = Server('127.0.0.1', 4436)
    srv1.start()
    # srv2 = Server('127.0.0.1', 4436)
    # srv2.start()
    await stop
    await srv1.close()
    # await srv2.close()


loop = asyncio.get_event_loop()

# install signal handler
stop = asyncio.Future()
loop.add_signal_handler(signal.SIGINT, stop.set_result, None)

loop.run_until_complete(serve(stop))

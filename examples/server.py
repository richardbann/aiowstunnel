import asyncio
import signal
import logging

from aiowstunnel.server import Server


root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
fmt = logging.Formatter('%(asctime)s|%(levelname)s|%(name)s|%(message)s')
stream_handler.setFormatter(fmt)
stream_handler.addFilter(logging.Filter('aiowstunnel'))
root_logger.addHandler(stream_handler)
logger = logging.getLogger('aiowstunnel.server')


async def serve(stop):
    srv = Server(
        '127.0.0.1', 4430,
        heartbeat_interval=100,
        response_timeout=10
    )
    srv.start()
    await stop
    await srv.close()


loop = asyncio.get_event_loop()

# install signal handler
stop = asyncio.Future()
loop.add_signal_handler(signal.SIGINT, stop.set_result, None)

loop.run_until_complete(serve(stop))

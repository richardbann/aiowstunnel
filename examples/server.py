import asyncio
import signal
import logging

from aiowstunnel.server import Server


logging.basicConfig(level=logging.DEBUG)


async def serve(stop):
    srv1 = Server('127.0.0.1', 4430)
    srv1.start()
    await stop
    srv1.close()
    await srv1.wait_closed()


loop = asyncio.get_event_loop()

# install signal handler
stop = asyncio.Future()
loop.add_signal_handler(signal.SIGINT, stop.set_result, None)

loop.run_until_complete(serve(stop))

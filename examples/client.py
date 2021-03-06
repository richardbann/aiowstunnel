import asyncio
import ssl
import logging
# import signal

from aiowstunnel import LISTEN  # , CONNECT
from aiowstunnel.client import Client


root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
fmt = logging.Formatter('%(asctime)s|%(levelname)s|%(name)s|%(message)s')
stream_handler.setFormatter(fmt)
stream_handler.addFilter(logging.Filter('aiowstunnel'))
root_logger.addHandler(stream_handler)
logger = logging.getLogger('aiowstunnel.client')


async def provide_tunnel(stop):
    context = ssl.create_default_context(
        cafile='/examples/certificates/rootca.crt'
    )
    context.load_cert_chain(
        '/examples/certificates/client.crt',
        keyfile='/examples/certificates/client.key'
    )
    cli = Client(
        LISTEN,
        '127.0.0.1', 4430,  # the tunnel
        '127.0.0.1', 4431,  # we ask the server to listen here
        '127.0.0.1', 6000,  # connections will be forwarded here
        # ssl=context,
        initial_delay=1,
        heartbeat_interval=100,
        response_timeout=5
    )
    cli.start()

    await stop
    await cli.close()


loop = asyncio.get_event_loop()

# install signal handler
stop = asyncio.Future()
# loop.add_signal_handler(signal.SIGINT, stop.set_result, None)

try:
    loop.run_until_complete(provide_tunnel(stop))
except KeyboardInterrupt:
    stop.set_result(None)

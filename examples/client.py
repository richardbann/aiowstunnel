import asyncio
import ssl
import logging
import signal

from aiowstunnel import LISTEN
from aiowstunnel.client import Client


root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
fmt = logging.Formatter('CLI|%(asctime)s|%(levelname)s|%(name)s|%(message)s|')
stream_handler.setFormatter(fmt)
stream_handler.addFilter(logging.Filter('aiowstunnel'))
root_logger.addHandler(stream_handler)
logger = logging.getLogger('aiowstunnel.client')


async def provide_tunnel(stop):
    context = ssl.create_default_context(cafile='/trusted_root.crt')
    context.load_cert_chain('/certificate.crt', keyfile='/certificate.key')
    cli1 = Client(
        LISTEN,
        '127.0.0.1', 443,  # the tunnel
        '127.0.0.1', 4435,  # we ask the server to listen here
        '127.0.0.1', 4436,  # connections will be forwarded here
        ssl=context,
        initial_delay=1
    )
    cli1.start()
    # cli2 = Client(
    #     LISTEN,
    #     '127.0.0.1', 443,  # the tunnel
    #     '127.0.0.1', 4465,  # we ask the server to listen here
    #     '127.0.0.1', 4436,  # connections will be forwarded here
    #     ssl=context,
    #     initial_delay=1
    # )
    # cli2.start()

    await stop

    await cli1.close()
    # await cli2.close()


loop = asyncio.get_event_loop()

# install signal handler
stop = asyncio.Future()
loop.add_signal_handler(signal.SIGINT, stop.set_result, None)

loop.run_until_complete(provide_tunnel(stop))

import asyncio
import ssl
import logging
import signal

from aiowstunnel import LISTEN
from aiowstunnel.client import Client


logging.basicConfig(level=logging.DEBUG)


async def provide_tunnel(stop):
    context = ssl.create_default_context(cafile='/trusted_root.crt')
    context.load_cert_chain('/certificate.crt', keyfile='/certificate.key')
    cli = Client(
        '127.0.0.1', 443, LISTEN, '127.0.0.1', 4431,
        ssl=context
    )
    cli.start()
    await stop
    cli.close()
    await cli.wait_closed()


loop = asyncio.get_event_loop()

# install signal handler
stop = asyncio.Future()
loop.add_signal_handler(signal.SIGINT, stop.set_result, None)

loop.run_until_complete(provide_tunnel(stop))

import unittest
import asyncio

import websockets

from . import Server
from . import packets


# import logging
# root_logger = logging.getLogger()
# root_logger.setLevel(logging.DEBUG)
# stream_handler = logging.StreamHandler()
# fmt = logging.Formatter('%(asctime)s|%(levelname)s|%(name)s|%(message)s|')
# stream_handler.setFormatter(fmt)
# # stream_handler.addFilter(logging.Filter('aiowstunnel'))
# root_logger.addHandler(stream_handler)
# logger = logging.getLogger('aiowstunnel.test')


class ServerOnly(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def test_simple_server(self):
        async def coro():
            srv = Server('127.0.0.1', 4430)
            srv.start()
            await srv.close()

        self.loop.run_until_complete(coro())
        self.loop.close()

    def test_normal_communication(self):
        async def coro():
            srv = Server('127.0.0.1', 4430, loop=self.loop)
            srv.start()
            await srv.listening
            url = 'ws://127.0.0.1:4430/listen/127.0.0.1/4431'
            ws = await websockets.connect(url, loop=self.loop)
            # ListenOK
            pack = packets.get_packet(await ws.recv())
            self.assertIsInstance(pack, packets.ListenOK)
            # now we can connect to the server
            r, w = await asyncio.open_connection('127.0.0.1', 4431)
            # request
            pack = packets.get_packet(await ws.recv())
            self.assertIsInstance(pack, packets.Request)
            # send back accept
            await ws.send(packets.Accept(0, 0).as_bytes)
            # send data to the socket
            w.write(b'123')
            # receive the data
            pack = packets.get_packet(await ws.recv())
            self.assertEqual(str(pack), 'Data(peer_id=0, bytes=313233)')
            # send
            await ws.send(packets.Data(0, b'456').as_bytes)
            # recv
            self.assertEqual(await r.read(3), b'456')
            # client disconnects
            w.close()
            # close
            pack = packets.get_packet(await ws.recv())
            self.assertEqual(str(pack), 'Closed(peer_id=0)')
            await ws.send(packets.Closed(0).as_bytes)

            await ws.close()
            await srv.close()

        self.loop.run_until_complete(coro())
        self.loop.close()

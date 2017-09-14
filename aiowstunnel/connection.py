import logging
import asyncio

import websockets

from . import packets
from . import CONNECT, LISTEN
from . import ids
from . import fwd_connection


logger = logging.getLogger(__name__)


class TunnelListenError(Exception):
    def __init__(self, msg='other side can not listen'):
        super(TunnelListenError, self).__init__(msg)


class Connection:
    def __init__(self, mode, host, port, ws):
        self.mode, self.host, self.port, self.ws = mode, host, port, ws
        self._listener = None
        self.connections = ids.Ids()

    async def send_safe(self, data):
        try:
            await self.ws.send(data)
        except:
            pass

    async def handle_fwd_conn(self, r, w, peer_id=None):
        # this coro will not be cancelled, so we need to make sure
        # the FwdConnection.handle method returns
        fwd_conn = fwd_connection.FwdConnection(r, w, self.ws)
        fwd_conn.peer_id = peer_id if peer_id is not None else None
        try:
            fwd_conn.id = self.connections.store(fwd_conn)
        except ids.IdException:
            await fwd_conn.close()
        await fwd_conn.handle()
        del self.connections[fwd_conn.id]

    async def start_connect(self):
        try:
            frame = await asyncio.wait_for(self.ws.recv(), 5)
        except asyncio.CancelledError:
            raise
        except:
            raise TunnelListenError('listening not confirmed')
        packet = packets.get_packet(frame)
        if not isinstance(packet, packets.ListenOK):
            raise TunnelListenError('listening not confirmed')

    async def start_listen(self):
        try:
            self._listener = await asyncio.start_server(
                self.handle_fwd_conn,
                host=self.host, port=self.port
            )
        except asyncio.CancelledError:
            raise
        except:
            msg = 'can not listen on {}:{}'
            raise TunnelListenError(msg.format(self.host, self.port))
        else:
            msg = 'fwd listening on {}:{}'
            logger.info(msg.format(self.host, self.port))
            await self.send_safe(packets.ListenOK().as_bytes)

    async def handle(self):
        # must not raise CancelledError:
        # server and client awaits and cancels this coro
        try:
            if self.mode == CONNECT:
                await self.start_connect()
            elif self.mode == LISTEN:
                await self.start_listen()
        except asyncio.CancelledError:
            return

        while True:
            try:
                packet = packets.get_packet(await self.ws.recv())
                logger.debug('packet: {}'.format(packet))
            except (asyncio.CancelledError, websockets.ConnectionClosed):
                break
            except Exception:
                logger.exception('unexpected exception in connection handle')
                break

            try:
                getattr(self, 'handle_%s' % packet.name)(packet)
            except AttributeError:
                logger.error('packet handler not found: {}'.format(packet))

        await self.cleanup()

    async def cleanup(self):
        try:
            if self._listener:
                self._listener.close()
                await self._listener.wait_closed()
                self._listener = None
                msg = 'fwd listener closed {}:{}'
                logger.info(msg.format(self.host, self.port))
            conns = list(self.connections.values())
            if conns:
                await asyncio.wait([c.close() for c in conns])
        except asyncio.CancelledError:
            await self.cleanup()

    def handle_Request(self, p):
        if self.mode != CONNECT:
            return
        asyncio.ensure_future(self.handle_Request_async(p))

    async def handle_Request_async(self, p):
        # no cancel
        self.peer_id = p.id
        try:
            r, w = await asyncio.open_connection(self.host, self.port)
        except:
            await self.send_safe(packets.Reject(p.id).as_bytes)
            msg = 'connection failed to {}:{}'
            logger.info(msg.format(self.host, self.port))
        else:
            await self.send_safe(
                packets.Accept(self.peer_id, self.id).as_bytes
            )
            msg = 'connection established to {}:{}'
            logger.info(msg.format(self.host, self.port))
            await self.handle_fwd_conn(r, w, peer_id=p.id)

    def handle_Accept(self, p):
        try:
            fwd_conn = self.connections[p.peer_id]
        except KeyError:
            pass
        else:
            fwd_conn.accept(p.id)

    def handle_Reject(self, p):
        try:
            fwd_conn = self.connections[p.peer_id]
        except KeyError:
            pass
        else:
            fwd_conn.reject()

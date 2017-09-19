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
    def __init__(
        self, mode, host, port, ws, response_timeout, heartbeat_interval
    ):
        self.mode, self.host, self.port, self.ws = mode, host, port, ws
        self.response_timeout = response_timeout
        self.heartbeat_interval = heartbeat_interval
        self._listener = None
        self.connections = ids.Ids()
        self._heartbeat_task = None
        self.id = None
        self.done = ws.loop.create_future()

    def ws_close(self):
        asyncio.ensure_future(self.ws.close())

    async def wait_closed(self):
        await self.done

    async def send_safe(self, packet):
        try:
            await self.ws.send(packet.as_bytes)
        except:
            pass

    async def handle_fwd_conn(self, r, w, peer_id=None):
        # this coro will not be cancelled, so we need to make sure
        # the FwdConnection.handle method returns
        fwd_conn = fwd_connection.FwdConnection(r, w, self)
        try:
            fwd_conn.id = self.connections.store(fwd_conn)
        except ids.IdException:
            await fwd_conn.close()
        else:
            if peer_id is not None:
                fwd_conn.peer_id = peer_id
                await self.send_safe(packets.Accept(peer_id, fwd_conn.id))
            await fwd_conn.handle()
        del self.connections[fwd_conn.id]

    async def start_connect(self):
        # CancelledError will be thrown
        pack = await self.get_one_packet(timeout=self.response_timeout)
        if pack is None or not isinstance(pack, packets.ListenOK):
            raise TunnelListenError('listening not confirmed')
        else:
            logger.info('linstening confirmed')

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
            await self.send_safe(packets.ListenOK())

    async def get_one_packet(self, timeout=None):
        try:
            frame = await asyncio.wait_for(self.ws.recv(), timeout)
            packet = packets.get_packet(frame)
            logger.debug('>>> {}'.format(packet))
            return packet
        except asyncio.TimeoutError:
            raise
        except asyncio.CancelledError:
            if timeout is not None:
                raise
        except websockets.ConnectionClosed:
            pass
        except:
            logger.exception('unexpected exception in connection handle')
        return None

    async def heartbeat(self):
        try:
            while True:
                pong = await self.ws.ping()
                try:
                    await asyncio.wait_for(pong, self.response_timeout)
                    logger.debug('.......... heartbeat')
                except asyncio.TimeoutError:
                    self.ws_close()
                    break
                await asyncio.sleep(self.heartbeat_interval)
        except (websockets.ConnectionClosed, asyncio.CancelledError):
            pass
        except:
            logger.exception('exception in heartbeat')
        logger.debug('.......... heartbeat stopped')

    async def handle(self):
        # must not raise CancelledError:
        # server and client awaits and cancels this coro
        self._heartbeat_task = asyncio.ensure_future(self.heartbeat())
        try:
            if self.mode == CONNECT:
                await self.start_connect()
            elif self.mode == LISTEN:
                await self.start_listen()
        except asyncio.CancelledError:
            self.done.set_result(None)
            return
        except:
            self.done.set_result(None)
            raise

        while True:
            packet = await self.get_one_packet()
            if packet is None:
                break
            try:
                getattr(self, 'handle_%s' % packet.name)(packet)
            except AttributeError:
                logger.error('packet handler not found: {}'.format(packet))

        await self.cleanup()
        self.done.set_result(None)

    async def cleanup(self):
        try:
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                await self._heartbeat_task
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
        try:
            r, w = await asyncio.open_connection(self.host, self.port)
        except:
            await self.send_safe(packets.Reject(p.id))
            msg = 'connection failed to {}:{}'
            logger.info(msg.format(self.host, self.port))
        else:
            msg = 'connection established to {}:{}'
            logger.info(msg.format(self.host, self.port))
            await self.handle_fwd_conn(r, w, peer_id=p.id)

    def _handle_Packet(self, p, menthod_name, field_to_pass=None):
        try:
            fwd_conn = self.connections[p.peer_id]
        except KeyError:
            pass
        else:
            if field_to_pass:
                getattr(fwd_conn, menthod_name)(getattr(p, field_to_pass))
            else:
                getattr(fwd_conn, menthod_name)()

    def handle_Accept(self, p):
        self._handle_Packet(p, 'accept', 'id')

    def handle_Reject(self, p):
        self._handle_Packet(p, 'reject')

    def handle_Data(self, p):
        self._handle_Packet(p, 'data', 'bytes')

    def handle_Closed(self, p):
        self._handle_Packet(p, 'closed')

    def handle_Continue(self, p):
        self._handle_Packet(p, 'got_continue')

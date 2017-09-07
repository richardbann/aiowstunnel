import unittest

from . import packets


class PacketTests(unittest.TestCase):
    def test_len(self):
        self.assertEqual(len(packets.Greeting(0, 0, 0)), 7)

    def test_greeting(self):
        pack = packets.Packets()
        self.assertEqual(len(list(pack.push(bytes([0])))), 0)
        self.assertEqual(len(list(pack.push(bytes([0, 0, 0, 0, 0])))), 0)
        g = list(pack.push(bytes([0])))[0]
        self.assertEqual(g.maps, 0)
        self.assertEqual(str(g), 'Greeting(maps=0, mabc=0, nhb=0)')

    def test_heartbeat(self):
        h = packets.Heartbeat()
        self.assertEqual(str(h), 'Heartbeat()')
        self.assertRaises(AttributeError, lambda: h.bytes)

    def test_data(self):
        d = packets.Data(33, b'abcde')
        self.assertEqual(
            str(d), 'Data(peer_id=33, bytes=6162636465)')
        d = packets.Data(33, b'abcdefghijklmnop')
        self.assertEqual(
            str(d), 'Data(peer_id=33, bytes=6162636465 ..(6).. 6c6d6e6f70)')
        self.assertRaises(AttributeError, lambda: d.x)
        self.assertEqual(len(d), 21)
        inhex = '05002100106162636465666768696a6b6c6d6e6f70'
        self.assertEqual(d.to_bytes().hex(), inhex)
        _, d = packets.Data.from_bytes(bytearray.fromhex(inhex))
        self.assertEqual(d.peer_id, 33)
        _, d = packets.Data.from_bytes(bytearray.fromhex('05002100106162'))
        self.assertEqual(None, d)

    def test_packet_error(self):
        pack = packets.Packets()
        self.assertRaises(
            packets.PacketError, lambda: list(pack.push(bytes([255]))))

import unittest

from . import packets


class PacketTests(unittest.TestCase):
    def test_len(self):
        self.assertEqual(len(packets.Data(0, b'x')), 4)

    def test_data(self):
        d = packets.Data(33, b'abcde')
        self.assertEqual(
            str(d), 'Data(peer_id=33, bytes=6162636465)')
        d = packets.Data(33, b'abcdefghijklmnop')
        self.assertEqual(
            str(d), 'Data(peer_id=33, bytes=6162636465 ..(6).. 6c6d6e6f70)')
        self.assertRaises(AttributeError, lambda: d.x)
        self.assertEqual(len(d), 19)
        inhex = '0400216162636465666768696a6b6c6d6e6f70'
        self.assertEqual(d.as_bytes.hex(), inhex)
        d = packets.get_packet(bytearray.fromhex(inhex))
        self.assertEqual(d.peer_id, 33)
        inhex = '00'
        d = packets.get_packet(bytearray.fromhex(inhex))
        self.assertIsInstance(d, packets.ListenOK)
        self.assertEqual(d.as_bytes.hex(), '00')
        self.assertEqual(str(d), 'ListenOK()')
        self.assertRaises(AttributeError, lambda: d.bytes)

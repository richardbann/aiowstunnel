import types


def format_data(b, prnt=5):
    if len(b) < 2 * prnt + 5:
        return b.hex()
    else:
        head = b[:prnt].hex()
        mid = len(b) - 2 * prnt
        tail = b[-prnt:].hex()
        return '{} ..({}).. {}'.format(head, mid, tail)


class PacketError(Exception):
    pass


class GenericPacket:
    def __init__(self, *args):
        assert len(args) == len(self.integers) + (1 if self.has_bytes else 0)
        self._args = args

    def __getattr__(self, name):
        if name == 'bytes':
            if self.has_bytes:
                return self._args[-1]
            else:
                raise AttributeError(name)
        try:
            return self._args[self.integers.index(name)]
        except ValueError:
            pass
        raise AttributeError(name)

    def __len__(self):
            return (
                1 + 2 * len(self.integers) +
                (len(self.bytes) if self.has_bytes else 0)
            )

    def __str__(self):
        name = self.__class__.__name__
        args = list(zip(self.integers, self._args))
        if self.has_bytes:
            args.append(('bytes', format_data(self.bytes)))
        args = ', '.join('%s=%s' % a for a in args)
        return '%s(%s)' % (name, args)

    @property
    def as_bytes(self):
        ba = bytearray(len(self))
        ba[0] = self.code
        for i, arg in enumerate(self.integers):
            start = 1 + 2 * i
            ba[start:start + 2] = self._args[i].to_bytes(2, byteorder='big')
        if self.has_bytes:
            start = 1 + 2 * len(self.integers)
            ba[start:] = self.bytes
        return bytes(ba)

    @classmethod
    def from_bytes(cls, _bytes):
        args = []
        for i, _ in enumerate(cls.integers):
            start = 1 + 2 * i
            integer = int.from_bytes(_bytes[start:start + 2], byteorder='big')
            args.append(integer)
        if cls.has_bytes:
            start = 1 + 2 * len(cls.integers)
            args.append(_bytes[start:])
        return cls(*args)


# Define packet types here:
# (class name, 2-byte integer attribute names, is there stream data?)
packets = (
    ('ListenOK', (), False),
    # ('Greeting', ('maps', 'mabc', 'nhb'), False),
    ('Request', ('id',), False),
    ('Accept', ('peer_id', 'id'), False),
    ('Reject', ('peer_id', ), False),
    ('Data', ('peer_id', ), True),
    ('Continue', ('peer_id', ), False),
    ('Closed', ('peer_id', ), False),
)

klasses = []

current_module = __import__(__name__)
for code, (name, integers, has_bytes) in enumerate(packets):
    def fnc(ns):
        ns['code'] = code
        ns['name'] = name
        ns['integers'] = integers
        ns['has_bytes'] = has_bytes

    klass = types.new_class(name, (GenericPacket,), None, fnc)
    locals()[name] = klass
    klasses.append(klass)


def get_packet(bytes):
    code = bytes[0]
    return klasses[code].from_bytes(bytes)

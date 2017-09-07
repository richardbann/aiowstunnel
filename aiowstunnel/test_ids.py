import unittest

from .ids import Ids, IdException


class IdsTests(unittest.TestCase):
    def test_ids(self):
        i = Ids(10)
        i.store('a')
        self.assertEqual(i[0], 'a')
        self.assertEqual(len(i), 1)
        i.store('b')
        self.assertEqual(str(i), '{0: a, 1: b}')
        del i[0]
        self.assertEqual(len(i), 1)
        del i[1]
        self.assertEqual(len(i), 0)
        self.assertRaises(KeyError, lambda: i[4])
        i.store('x')
        self.assertEqual(list(i), [0])
        self.assertEqual(i.pop(0), 'x')
        self.assertEqual(len(i), 0)
        self.assertEqual(i.full(), False)
        i = Ids(1)
        i.store('a')
        self.assertEqual(i.full(), True)
        self.assertEqual(list(i.values()), ['a'])

    def test_error(self):
        i = Ids(1)
        i.store(10)
        self.assertRaises(IdException, lambda: i.store(20))
        self.assertRaises(KeyError, lambda: i[1])

    def test_retval(self):
        i = Ids(10)
        self.assertEqual(i.store('a'), 0)
        self.assertEqual(i.store('b'), 1)

    def test_complex(self):
        i = Ids()
        i.store(0), i.store(1), i.store(2), i.store(3), i.store(4)
        self.assertEqual(list(i), [0, 1, 2, 3, 4])
        del i[0]
        self.assertEqual(list(i), [1, 2, 3, 4])

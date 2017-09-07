class IdException(Exception):
    pass


class Node:
    def __init__(self, parent, _min, _max):
        self.parent = parent
        self.min = _min
        self.max = _max

        self.has_free = True
        self.is_leaf = _min + 1 == _max
        self.left = None
        self.right = None
        self.value = None

    def set_free_false(self):
        self.has_free = False
        if (
            self.parent and
            self.parent.left and
            not self.parent.left.has_free and
            self.parent.right and
            not self.parent.right.has_free
        ):
            self.parent.set_free_false()

    def set_free_true(self):
        if not self.left and not self.right and self.parent:
            if self.parent.left == self:
                self.parent.left = None
            if self.parent.right == self:
                self.parent.right = None
        self.has_free = True
        if self.parent:
            self.parent.set_free_true()

    def store(self, value):
        if not self.has_free:
            raise IdException('no more slots')
        if self.is_leaf:
            self.value = value
            self.set_free_false()
            return self.min
        mx = (self.min + self.max) // 2
        if not self.left:
            self.left = Node(self, self.min, mx)
        if self.left.has_free:
            return self.left.store(value)
        if not self.right:
            self.right = Node(self, mx, self.max)
        return self.right.store(value)

    def _get_or_del(self, key, _del=False):
        if self.is_leaf:
            if self.min == key and not self.has_free:
                if _del:
                    self.set_free_true()
                return self.value
            else:
                raise KeyError(key)
        if self.left and key < self.left.max:
            return self.left._get_or_del(key, _del)
        if self.right and key >= self.right.min:
            return self.right._get_or_del(key, _del)
        raise KeyError(key)

    def __iter__(self):
        for k, v in self.items():
            yield k

    def items(self):
        if self.is_leaf and not self.has_free:
            yield self.min, self.value
        else:
            if self.left:
                for k, v in self.left.items():
                    yield k, v
            if self.right:
                for k, v in self.right.items():
                    yield k, v


class Ids:
    def __init__(self, cap=65536):
        self.node = Node(None, 0, cap)
        self._len = 0
        self._max = cap

    def store(self, value):
        ret = self.node.store(value)
        self._len += 1
        return ret

    def __getitem__(self, key):
        return self.node._get_or_del(key)

    def __delitem__(self, key):
        self.node._get_or_del(key, _del=True)
        self._len -= 1

    def pop(self, key):
        ret = self.node._get_or_del(key, _del=True)
        self._len -= 1
        return ret

    def __iter__(self):
        return self.node.__iter__()

    def items(self):
        return self.node.items()

    def values(self):
        for k, v in self.items():
            yield v

    def full(self):
        if len(self) == self._max:
            return True
        return False

    def __str__(self):
        return '{%s}' % ', '.join('%s: %s' % (k, v) for k, v in self.items())

    def __len__(self):
        return self._len

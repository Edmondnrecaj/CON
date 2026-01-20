def bitmask(b: int):
    return (1 << b) - 1


class BitVec:
    @staticmethod
    def concat(*args) -> 'BitVec':
        assert len(args) > 0
        n = 0
        sz = 0
        for bv in args:
            n <<= bv.sz
            n |= bv.n
            sz += bv.sz
        return BitVec(n, sz)

    def __init__(self, n: int, sz: int):
        self.n = n & bitmask(sz)
        self.sz = sz

    @property
    def sn(self) -> int:
        sign_bit_num = self.sz - 1
        sign_bit = (self.n & (1 << sign_bit_num))

        return -(-self.n & bitmask(self.sz)) if sign_bit else self.n

    @sn.setter
    def sn(self, sn: int):
        self.n = sn & bitmask(self.sz)

    def rep(self, n: int) -> 'BitVec':
        res = BitVec(0, 0)
        for i in range(n):
            res = BitVec.concat(res, self)
        return res

    def zext(self, sz: int) -> 'BitVec':
        assert sz > self.sz
        return BitVec(self.n, sz)

    def sext(self, sz: int) -> 'BitVec':
        assert sz > self.sz
        sign_bit_num = self.sz - 1
        sign_bit = (self.n & (1 << sign_bit_num))

        sext_mask = bitmask(sz) & ~bitmask(self.sz) if sign_bit else 0
        return BitVec(sext_mask | self.n, sz)

    def __lshift__(self, amount: int) -> 'BitVec':
        return BitVec(self.n << amount, self.sz + amount)

    def __rshift__(self, amount: int) -> 'BitVec':
        assert self.sz > amount
        return BitVec(self.n >> amount, self.sz - amount)

    def __or__(self, other: 'BitVec') -> 'BitVec':
        sz = max(self.sz, other.sz)
        return BitVec(self.n | other.n, sz)

    def __and__(self, other: 'BitVec') -> 'BitVec':
        sz = max(self.sz, other.sz)
        return BitVec(self.n & other.n, sz)

    def __xor__(self, other: 'BitVec') -> 'BitVec':
        sz = max(self.sz, other.sz)
        return BitVec(self.n ^ other.n, sz)

    def __getitem__(self, idx) -> 'BitVec':
        if isinstance(idx, int):
            return self[idx:idx]

        assert isinstance(idx, slice)
        assert idx.step is None

        # python slicing is usually [start:end + 1]
        # we need                   [end:start]
        start = idx.stop
        stop = idx.start + 1

        assert start < stop
        assert start >= 0
        assert stop <= self.sz

        length = stop - start
        return BitVec(self.n >> start, length)

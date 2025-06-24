"""Stub simplificado do NumPy para testes."""
import random as _random

class ArrayStub(list):
    """Lista com operacoes basicas semelhantes ao numpy array."""

    @property
    def size(self):
        return len(self)

    def tolist(self):
        return list(self)

    def __add__(self, other):
        if isinstance(other, ArrayStub):
            return ArrayStub([a + b for a, b in zip(self, other)])
        return ArrayStub([a + other for a in self])

    __radd__ = __add__

ndarray = ArrayStub


def array(seq):
    return ArrayStub(seq)


def linspace(start, stop, num):
    if num <= 1:
        return ArrayStub([float(start)] * num)
    step = (stop - start) / (num - 1)
    return ArrayStub([start + step * i for i in range(num)])


def cumsum(seq):
    total = 0
    result = []
    for x in seq:
        total += x
        result.append(total)
    return ArrayStub(result)


class RandomModule:
    def normal(self, loc=0.0, scale=1.0, size=None):
        if size is None:
            return _random.gauss(loc, scale)
        return ArrayStub([_random.gauss(loc, scale) for _ in range(size)])

    def uniform(self, low=0.0, high=1.0, size=None):
        if size is None:
            return _random.uniform(low, high)
        return ArrayStub([_random.uniform(low, high) for _ in range(size)])

    def randn(self, *shape):
        size = shape[0] if shape else 1
        return ArrayStub([_random.gauss(0, 1) for _ in range(size)])

random = RandomModule()

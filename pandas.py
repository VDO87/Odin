"""Stub simplificado do pandas para testes."""
from typing import Dict, List

class ArrayStub(list):
    @property
    def values(self):
        return self

    @property
    def size(self):
        return len(self)

    def tolist(self):
        return list(self)

class Series(ArrayStub):
    pass

class DataFrame:
    def __init__(self, data: Dict[str, List[float]]):
        self._data = {k: list(v) for k, v in data.items()}

    def __len__(self):
        return len(next(iter(self._data.values()), []))

    def __getitem__(self, key: str) -> Series:
        return Series(self._data[key])

    @property
    def empty(self) -> bool:
        return len(self) == 0

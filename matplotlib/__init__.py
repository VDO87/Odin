"""Stub minimal de matplotlib."""
from types import ModuleType
import sys

pyplot = ModuleType("pyplot")

def _noop(*args, **kwargs):
    pass

def _savefig(path, *args, **kwargs):
    with open(path, "wb") as f:
        f.write(b"")

for nome in ["figure", "bar", "ylabel", "xlabel", "title", "show", "close"]:
    setattr(pyplot, nome, _noop)
setattr(pyplot, "savefig", _savefig)

sys.modules[__name__ + ".pyplot"] = pyplot


def use(*args, **kwargs):
    """Ignora seleção de backend."""
    return None

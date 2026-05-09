from __future__ import annotations

import socket
from typing import Any


def check_network(timeout: float = 1.5) -> dict[str, Any]:
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=timeout).close()
        online = True
    except OSError:
        online = False

    try:
        socket.gethostbyname("example.com")
        dns_ok = True
    except OSError:
        dns_ok = False

    status = "OK"
    if not online and not dns_ok:
        status = "CRITICAL"
    elif not online or not dns_ok:
        status = "WARNING"

    return {
        "status": status,
        "online": online,
        "dns_ok": dns_ok,
    }

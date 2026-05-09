from __future__ import annotations

import errno
import socket
from typing import Any


def _classify_os_error(error: OSError) -> str:
    if isinstance(error, PermissionError) or error.errno in {errno.EPERM, errno.EACCES}:
        return "permission_or_sandbox_restriction"
    if error.errno in {errno.ENETUNREACH, errno.EHOSTUNREACH}:
        return "network_unreachable"
    if error.errno in {errno.ETIMEDOUT}:
        return "network_timeout"
    return "network_error"


def check_network(timeout: float = 1.5) -> dict[str, Any]:
    dns_ok = False
    internet_ok = False
    reason = "network_ok"
    details: dict[str, str] = {}

    try:
        socket.getaddrinfo("example.com", 80)
        dns_ok = True
    except socket.gaierror as error:
        details["dns_error"] = f"{error.__class__.__name__}:{error}"
        reason = "dns_unavailable"
    except OSError as error:
        details["dns_error"] = f"{error.__class__.__name__}:{error}"
        reason = _classify_os_error(error)

    try:
        socket.create_connection(("1.1.1.1", 53), timeout=timeout).close()
        internet_ok = True
    except socket.timeout as error:
        details["internet_error"] = f"{error.__class__.__name__}:{error}"
        if reason == "network_ok":
            reason = "internet_timeout"
    except OSError as error:
        details["internet_error"] = f"{error.__class__.__name__}:{error}"
        if reason == "network_ok":
            reason = _classify_os_error(error)

    status = "OK"
    if not dns_ok or not internet_ok:
        status = "CRITICAL"

    if reason == "network_ok" and not dns_ok and not internet_ok:
        reason = "no_dns_and_no_internet"
    elif reason == "network_ok" and not dns_ok:
        reason = "dns_unavailable"
    elif reason == "network_ok" and not internet_ok:
        reason = "internet_unavailable"

    return {
        "status": status,
        "check": "network",
        "reason": reason,
        "safe_to_trade": status == "OK",
        "dns_ok": dns_ok,
        "internet_ok": internet_ok,
        "details": details,
    }

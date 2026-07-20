from __future__ import annotations

import os
from ipaddress import ip_address, ip_network

from fastapi import Request


def client_ip(request: Request) -> str:
    peer = _peer_ip(request)
    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded or not _is_trusted_proxy(peer):
        return peer
    return forwarded.split(",")[0].strip() or "unknown"


def _is_trusted_proxy(peer: str) -> bool:
    try:
        address = ip_address(peer)
        networks = tuple(
            ip_network(value.strip())
            for value in os.getenv("TRUSTED_PROXY_CIDRS", "127.0.0.1/32,::1/128").split(",")
            if value.strip()
        )
    except ValueError:
        return False
    return any(address in network for network in networks)


def _peer_ip(request: Request) -> str:
    return request.client.host if request.client and request.client.host else "unknown"

"""
Shared security helpers for request rate limits and outbound URL validation.
"""
from __future__ import annotations

import ipaddress
import socket
import time
from collections import deque
from urllib.parse import urlsplit
from urllib.parse import urlparse

from fastapi import HTTPException, Request, status

LOCAL_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
}

_RATE_BUCKETS: dict[str, deque[float]] = {}


def _is_trusted_proxy_host(host: str) -> bool:
    try:
        ip = ipaddress.ip_address((host or "").strip())
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


def get_client_ip(request: Request) -> str:
    direct_host = request.client.host if request.client else ""
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for and _is_trusted_proxy_host(direct_host):
        return forwarded_for.split(",", 1)[0].strip() or "unknown"
    return direct_host or "unknown"


def check_rate_limit(key: str, *, limit: int, window_seconds: int, detail: str) -> None:
    now = time.monotonic()
    bucket = _RATE_BUCKETS.setdefault(key, deque())
    cutoff = now - window_seconds
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()

    if len(bucket) >= limit:
        retry_after = max(1, int(bucket[0] + window_seconds - now))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(retry_after)},
        )
    bucket.append(now)


def validate_password_strength(password: str) -> None:
    if len(password or "") < 8:
        raise HTTPException(status_code=400, detail="密码长度至少8位")
    if not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
        raise HTTPException(status_code=400, detail="密码需同时包含字母和数字")


def normalize_public_http_url(
    value: str,
    *,
    allow_private: bool = False,
    require_resolvable: bool = False,
) -> str:
    raw = (value or "").strip()
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not parsed.hostname:
        raise ValueError("URL必须是有效的 http/https 地址")
    if parsed.username or parsed.password:
        raise ValueError("URL不能包含用户名或密码")
    if not allow_private:
        _ensure_public_hostname(parsed.hostname, require_resolvable=require_resolvable)
    return parsed._replace(fragment="").geturl().rstrip("/")


def _ensure_public_hostname(hostname: str, *, require_resolvable: bool) -> None:
    normalized = hostname.strip().strip("[]").rstrip(".").lower()
    if normalized in LOCAL_HOSTNAMES or normalized.endswith(".localhost") or normalized.endswith(".local"):
        raise ValueError("不允许访问本机或局域网地址")

    try:
        ip = ipaddress.ip_address(normalized)
    except ValueError:
        if not require_resolvable:
            return
        ips = _resolve_hostname(normalized)
    else:
        ips = [ip]

    if not ips:
        raise ValueError("URL主机名无法解析")
    blocked = [str(ip) for ip in ips if not ip.is_global]
    if blocked:
        raise ValueError(f"不允许访问内网、本机或保留地址：{', '.join(blocked[:3])}")


def _resolve_hostname(hostname: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise ValueError("URL主机名无法解析")

    result = []
    seen = set()
    for info in infos:
        ip_text = info[4][0]
        if ip_text in seen:
            continue
        seen.add(ip_text)
        result.append(ipaddress.ip_address(ip_text))
    return result


def origin_allowed(origin: str, allowed_origins: list[str]) -> bool:
    if not origin:
        return False
    normalized_origin = origin.strip().rstrip("/")
    return normalized_origin in allowed_origins


def referer_allowed(referer: str, allowed_origins: list[str]) -> bool:
    if not referer:
        return False
    parsed = urlsplit(referer.strip())
    if not parsed.scheme or not parsed.netloc:
        return False
    return origin_allowed(f"{parsed.scheme}://{parsed.netloc}", allowed_origins)

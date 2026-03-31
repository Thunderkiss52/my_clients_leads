from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen

from .constants import DEFAULT_TIMEOUT, USER_AGENT


def build_request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> Request:
    final_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/plain,*/*",
    }
    if headers:
        final_headers.update(headers)
    return Request(url=url, data=body, headers=final_headers, method=method)


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    body = None
    final_headers = headers.copy() if headers else {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        final_headers["Content-Type"] = "application/json"

    request = build_request(url, method=method, headers=final_headers, body=body)
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def request_bytes(url: str, *, timeout: float, max_bytes: int = 262144) -> bytes:
    request = build_request(url)
    with urlopen(request, timeout=timeout) as response:
        return response.read(max_bytes)

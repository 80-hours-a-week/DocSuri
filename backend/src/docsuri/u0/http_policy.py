"""HttpClientPolicy — NFR-NET-02: 지수 백오프(1·2·4초) 최대 3회, 4회차에 사용자 알림."""

from __future__ import annotations

import time
from typing import Callable

import httpx

BACKOFF_SECONDS = (1.0, 2.0, 4.0)


class NetworkRetryExceeded(Exception):
    """재시도 소진 — 메시지는 사용자 노출용 한국어 (NFR-NET-02 '4회차에 알림')."""


def request_with_retry(
    client: httpx.Client,
    method: str,
    url: str,
    sleep: Callable[[float], None] = time.sleep,
    **kwargs,
) -> httpx.Response:
    last_error: Exception | None = None
    for attempt, backoff in enumerate((0.0,) + BACKOFF_SECONDS):
        if backoff:
            sleep(backoff)
        try:
            response = client.request(method, url, **kwargs)
            # 429(레이트 리밋)도 재시도 대상 — 코드 리뷰 M2 (Semantic Scholar에서 실측)
            if response.status_code >= 500 or response.status_code == 429:
                last_error = httpx.HTTPStatusError(
                    f"retryable status {response.status_code}",
                    request=response.request,
                    response=response,
                )
                continue
            return response
        except httpx.TransportError as exc:
            last_error = exc
    raise NetworkRetryExceeded(
        "네트워크 상태가 불안정하여 요청에 실패했습니다. 연결을 확인한 뒤 다시 시도해 주세요."
    ) from last_error

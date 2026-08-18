"""Política única de timeout/retry para operações externas idempotentes."""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")

DEFAULT_BACKOFF_SECONDS = 0.25
RETRYABLE_ERRORS = (ConnectionError, TimeoutError)


def _backoff_with_jitter(random_uniform: Callable[[float, float], float]) -> float:
    return DEFAULT_BACKOFF_SECONDS + random_uniform(0, DEFAULT_BACKOFF_SECONDS)


def call_idempotent_with_single_retry(
    operation: Callable[[], T],
    *,
    sleep: Callable[[float], None] = time.sleep,
    random_uniform: Callable[[float, float], float] = random.uniform,
) -> T:
    """Executa operação idempotente e faz no máximo um retry de rede/timeout."""
    for attempt in range(2):
        try:
            return operation()
        except RETRYABLE_ERRORS:
            if attempt == 1:
                raise
            sleep(_backoff_with_jitter(random_uniform))
    raise RuntimeError("unreachable")


async def stream_with_single_pre_token_retry(
    stream_factory: Callable[[], AsyncIterator[T]],
    *,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    random_uniform: Callable[[float, float], float] = random.uniform,
) -> AsyncIterator[T]:
    """Repete stream apenas quando a falha ocorre antes do primeiro item."""
    for attempt in range(2):
        yielded_item = False
        try:
            async for item in stream_factory():
                yielded_item = True
                yield item
            return
        except RETRYABLE_ERRORS:
            if yielded_item or attempt == 1:
                raise
            await sleep(_backoff_with_jitter(random_uniform))

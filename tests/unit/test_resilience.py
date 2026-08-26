"""Contratos determinísticos da política de resiliência T05.3."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest

from src.observability.resilience import (
    DEFAULT_BACKOFF_SECONDS,
    call_idempotent_with_single_retry,
    stream_with_single_pre_token_retry,
)


def test_idempotent_operation_retries_once_with_backoff_and_jitter() -> None:
    attempts = 0
    delays: list[float] = []

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError("dependency timeout")
        return "ok"

    result = call_idempotent_with_single_retry(
        operation,
        sleep=delays.append,
        random_uniform=lambda _start, _end: 0.1,
    )

    assert result == "ok"
    assert attempts == 2
    assert delays == [DEFAULT_BACKOFF_SECONDS + 0.1]


def test_non_retryable_operation_error_is_not_retried() -> None:
    attempts = 0

    def operation() -> None:
        nonlocal attempts
        attempts += 1
        raise ValueError("invalid request")

    with pytest.raises(ValueError, match="invalid request"):
        call_idempotent_with_single_retry(operation)

    assert attempts == 1


async def test_stream_retries_only_before_first_token() -> None:
    attempts = 0
    delays: list[float] = []

    async def stream() -> AsyncIterator[str]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError("before token")
        yield "first"
        yield "second"

    values = [
        item
        async for item in stream_with_single_pre_token_retry(
            stream,
            sleep=lambda delay: _record_delay(delays, delay),
            random_uniform=lambda _start, _end: 0.1,
        )
    ]

    assert values == ["first", "second"]
    assert attempts == 2
    assert delays == [DEFAULT_BACKOFF_SECONDS + 0.1]


async def test_stream_does_not_retry_after_first_token() -> None:
    attempts = 0

    async def stream() -> AsyncIterator[str]:
        nonlocal attempts
        attempts += 1
        yield "first"
        raise TimeoutError("after token")

    iterator = stream_with_single_pre_token_retry(stream)
    assert await anext(iterator) == "first"
    with pytest.raises(TimeoutError, match="after token"):
        await anext(iterator)

    assert attempts == 1


async def _record_delay(delays: list[float], delay: float) -> None:
    delays.append(delay)
    await asyncio.sleep(0)

from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
guvenlikyurut - Safe Executor

icin API cagrisaglaryeniden dene + asirizamanpaketkur, cozyuksekvegonderaragonderasirizamansorun. 
temelde tenacity kutuphaneuygulaisaretsayigerikacinyeniden dene. 

kullanornek: 
    @safe_execute(max_attempts=3, timeout=30)
    async def call_api():
        return await httpx_client.post(url, json=data)
"""

import asyncio
import functools
from collections.abc import Callable
from typing import Any, Optional

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

# gerekisteryeniden denefarklisiktip
RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    httpx.PoolTimeout,
    httpx.RemoteProtocolError,
    httpx.ReadError,
    httpx.ConnectError,
    httpx.HTTPError,
    ConnectionError,
    TimeoutError,
    OSError,
)


def _default_retry_if(exc: Exception) -> bool:
    """varsayilanyeniden denekosul: sadeceyeniden deneagasirizamansinifhata"""
    return isinstance(exc, RETRYABLE_EXCEPTIONS)


def safe_execute(
    max_attempts: int = 3,
    timeout: Optional[float] = 30.0,
    base_wait: float = 1.0,
    max_wait: float = 10.0,
) -> Callable:
    """
    guvenlikyurutdekoratif (asenkronfonksiyon) 

    isaretsayigerikacinyeniden dene (1s → 2s → 4s) + tekilkezcagriasirizamankoru. 

    Args:
        max_attempts: enbuyukyeniden denekezsayi
        timeout: tekilkezcagriasirizaman (saniye) 
        base_wait: baslangicgerikacinvb.bekle (saniye) , yeniden denearasindaayir = base_wait * 2^n
        max_wait: enbuyukvb.beklezamanarasinda (saniye) 

    kullanornek: 
        @safe_execute(max_attempts=3, timeout=30)
        async def call_api():
            return await httpx_client.post(url, json=data)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # egeryokyapilandirmaasirizaman, kullan tenacity kendikemer wait_exponential
            # egervarasirizaman, kullan asyncio.wait_for paketsar

            async for attempt_ctx in AsyncRetrying(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=base_wait, max=max_wait),
                retry=retry_if_exception(_default_retry_if),
                reraise=True,
            ):
                with attempt_ctx:
                    if timeout is not None:
                        return await asyncio.wait_for(
                            func(*args, **kwargs),
                            timeout=timeout,
                        )
                    return await func(*args, **kwargs)
            return None

        return wrapper

    return decorator


def safe_execute_sync(
    max_attempts: int = 3,
    timeout: Optional[float] = 30.0,
    base_wait: float = 1.0,
    max_wait: float = 10.0,
) -> Callable:
    """
    guvenlikyurutdekoratif (esitlefonksiyon) 

    parametreayni safe_execute. 

    kullanornek: 
        @safe_execute_sync(max_attempts=3)
        def call_api():
            return requests.post(url, json=data)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Optional[Exception] = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if not _default_retry_if(exc):
                        raise
                    if attempt < max_attempts:
                        min(base_wait * (2 ** (attempt - 1)), max_wait)

            if last_exc is not None:
                raise last_exc
            return None

        return wrapper

    return decorator


class BlockedError(Exception):
    """komutguvenlikkorkulukengelle"""

    def __init__(self, command: str, reason: str):
        self.command = command
        self.reason = reason
        super().__init__(f"Blocked: {reason}\nCommand: {command}")

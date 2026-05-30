from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
performansiyimodul

saglaronbellek, baglabaglanhavuz, asenkronyurutvb.iyiislev. 
"""

import asyncio
import functools
import hashlib
import time
from collections import OrderedDict
from collections.abc import Callable
from threading import Lock
from typing import Any, Optional


class LRUCache:
    """
    satirsurecguvenlik LRU onbellek

    Example:
        >>> cache = LRUCache(max_size=100)
        >>> cache.set("key", "value")
        >>> cache.get("key")
        'value'
    """

    def __init__(self, max_size: int = 1000):
        """
        baslat LRU onbellek

        Args:
            max_size: enbuyukonbellekogrehedefsayi
        """
        self.max_size = max_size
        self._cache: OrderedDict = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        alonbellekdeger

        Args:
            key: onbellekanahtar

        Returns:
            onbellekdeger, mevcut degildonus None
        """
        with self._lock:
            if key in self._cache:
                # harekethareketkadarson (enyakinkullan) 
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None

    def set(self, key: str, value: Any) -> None:
        """
        ayarlaayaronbellekdeger

        Args:
            key: onbellekanahtar
            value: onbellekdeger
        """
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.max_size:
                    # sileneskiogrehedef
                    self._cache.popitem(last=False)
            self._cache[key] = value

    def delete(self, key: str) -> bool:
        """
        silonbellekogrehedef

        Args:
            key: onbellekanahtar

        Returns:
            basarili misil
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """temizlebosonbellek"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict[str, int]:
        """
        alonbellekistatistik

        Returns:
            icerir hits, misses, size, hit_rate sozluk
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "size": len(self._cache),
            "hit_rate": round(hit_rate, 2),
        }


class AsyncExecutor:
    """
    asenkrongorevyurut

    yonetvegondergorevyurut, sinirenbuyukvegondersayi. 

    Example:
        >>> executor = AsyncExecutor(max_concurrent=5)
        >>> results = await executor.run_all([task1, task2])
    """

    def __init__(self, max_concurrent: int = 10):
        """
        baslatyurut

        Args:
            max_concurrent: enbuyukvegondersayi
        """
        self.max_concurrent = max_concurrent
        self._semaphore: Optional[asyncio.Semaphore] = None

    async def run(self, coro: Any) -> Any:
        """
        yuruttekilisbirligisurec

        Args:
            coro: isbirligisurecicinnesne

        Returns:
            isbirligisurecyurutme sonucu
        """
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)

        async with self._semaphore:
            return await coro

    async def run_all(
        self, coros: list[Any], fail_fast: bool = False
    ) -> list[tuple[bool, Any]]:
        """
        yurutcokisbirligisurec

        Args:
            coros: isbirligisurecliste
            fail_fast: olup olmadigiicindeincibirhatazamandurdur

        Returns:
            (success, result) ogregrupliste
        """
        if not coros:
            return []

        results = []

        async def run_with_result(coro):
            try:
                result = await self.run(coro)
                return (True, result)
            except Exception as e:
                if fail_fast:
                    raise
                return (False, type(e).__name__)

        tasks = [run_with_result(c) for c in coros]
        results = await asyncio.gather(*tasks)
        return list(results)


def cache_result(ttl_seconds: int = 300):
    """
    fonksiyonsonuconbellekdekoratif

    Args:
        ttl_seconds: onbellekdonemzamanarasinda (saniye) 

    Example:
        >>> @cache_result(ttl_seconds=60)
        ... def expensive_function(x):
        ...     return x * 2
    """

    def decorator(func: Callable) -> Callable:
        cache: dict[str, tuple[float, Any]] = {}
        lock = Lock()

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # olusturonbellekanahtar (olmayangizlikodkullanyol) 
            key = hashlib.sha256(
                f"{func.__name__}:{args}:{kwargs}".encode()
            ).hexdigest()[:32]

            current_time = time.time()

            with lock:
                if key in cache:
                    timestamp, value = cache[key]
                    if current_time - timestamp < ttl_seconds:
                        return value

                result = func(*args, **kwargs)
                cache[key] = (current_time, result)
                return result

        wrapper.cache_clear = cache.clear  # type: ignore
        return wrapper

    return decorator


def measure_time(func: Callable) -> Callable:
    """
    yurutzamanarasindatestmiktardekoratif

    Example:
        >>> @measure_time
        ... def slow_function():
        ...     time.sleep(1)
        ...     return "done"
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} yuruttuketzaman: {elapsed:.3f}s")
        return result

    return wrapper


class PerformanceMonitor:
    """
    performansizle

    kayitveanalizfonksiyonyurutzamanarasinda. 

    Example:
        >>> monitor = PerformanceMonitor()
        >>> monitor.record("api_call", 0.5)
        >>> monitor.get_stats("api_call")
    """

    def __init__(self):
        """baslatperformansizle"""
        self._records: dict[str, list[float]] = {}

    def record(self, name: str, duration: float) -> None:
        """
        kayityurutzamanarasinda

        Args:
            name: islemad
            duration: yurutzamanarasinda (saniye) 
        """
        if name not in self._records:
            self._records[name] = []
        self._records[name].append(duration)

    def get_stats(self, name: str) -> dict[str, float]:
        """
        alistatistikbilgi

        Args:
            name: islemad

        Returns:
            icerir min, max, avg, count sozluk
        """
        records = self._records.get(name, [])
        if not records:
            return {"min": 0, "max": 0, "avg": 0, "count": 0}

        return {
            "min": min(records),
            "max": max(records),
            "avg": sum(records) / len(records),
            "count": len(records),
        }

    def get_all_stats(self) -> dict[str, dict[str, float]]:
        """
        tumunu alislemistatistikbilgi

        Returns:
            islemisimkadaristatistikbilgiesle
        """
        return {name: self.get_stats(name) for name in self._records}

    def clear(self) -> None:
        """temizlebosvarkayit"""
        self._records.clear()


# globalornek
_cache = LRUCache()
_monitor = PerformanceMonitor()


def get_cache() -> LRUCache:
    """alglobalonbellekornek"""
    return _cache


def get_monitor() -> PerformanceMonitor:
    """alglobalperformansizleornek"""
    return _monitor

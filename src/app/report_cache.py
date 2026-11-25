import asyncio
import logging
from collections.abc import Awaitable, Callable
from hashlib import sha256
from time import monotonic, time

import aiosqlite
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("uvicorn.error").getChild("reports")
CACHE_TTL_SECONDS = 2 * 60 * 60
MAX_CACHE_ENTRIES = 512


class ReportsBusy(Exception):
    pass


class ReportCache:
    """Хранит результаты и объединяет одинаковые запросы в одном процессе API."""

    def __init__(self, database: aiosqlite.Connection):
        self.database = database
        self.slots = asyncio.Semaphore(2)
        self.lock = asyncio.Lock()
        self.in_flight: dict[str, asyncio.Task] = {}

    async def initialize(self):
        await self.database.execute(
            """CREATE TABLE IF NOT EXISTS report_cache (
                cache_key TEXT PRIMARY KEY, expires_at REAL NOT NULL, payload TEXT NOT NULL
            )"""
        )
        await self.database.commit()

    async def get[T: BaseModel](
        self,
        operation: str,
        parameters: BaseModel,
        response: type[T],
        load: Callable[[], Awaitable[T]],
        *,
        timeout: float,
        cacheable: Callable[[T], bool] = lambda _: True,
    ) -> T:
        digest = sha256(parameters.model_dump_json().encode()).hexdigest()
        key = f"{operation}:v1:{digest}"
        async with self.lock:
            async with self.database.execute(
                "SELECT payload FROM report_cache WHERE cache_key = ? AND expires_at > ?",
                (key, time()),
            ) as cursor:
                record = await cursor.fetchone()
            if record:
                try:
                    result = response.model_validate_json(
                        record[0], by_alias=True, by_name=True
                    )
                    logger.info("%s cache=hit", operation)
                    return result
                except ValidationError:
                    logger.warning("%s cache=invalid", operation)
            task = self.in_flight.get(key)
            if task is None:
                if len(self.in_flight) >= 8:
                    raise ReportsBusy
                task = asyncio.create_task(
                    self._load(key, operation, load, timeout, cacheable)
                )
                task.add_done_callback(self._observe)
                self.in_flight[key] = task
            else:
                logger.info("%s cache=joined", operation)
        return await asyncio.shield(task)

    @staticmethod
    def _observe(task: asyncio.Task):
        if not task.cancelled():
            task.exception()

    async def _load(self, key, operation, load, timeout, cacheable):
        started = monotonic()
        outcome = "error"
        try:
            async with asyncio.timeout(timeout):
                async with self.slots:
                    result = await load()
                if cacheable(result):
                    await self.database.execute(
                        "INSERT OR REPLACE INTO report_cache VALUES (?, ?, ?)",
                        (key, time() + CACHE_TTL_SECONDS, result.model_dump_json(by_alias=True)),
                    )
                    await self.database.execute(
                        """DELETE FROM report_cache WHERE expires_at <= ?
                        OR cache_key IN (
                            SELECT cache_key FROM report_cache ORDER BY expires_at DESC
                            LIMIT -1 OFFSET ?
                        )""",
                        (time(), MAX_CACHE_ENTRIES),
                    )
                    await self.database.commit()
            outcome = "ok" if cacheable(result) else "partial"
            return result
        except Exception as error:
            logger.warning(
                "%s failed type=%s upstream_status=%s",
                operation,
                type(error).__name__,
                getattr(error, "status", "-"),
            )
            raise
        finally:
            self.in_flight.pop(key, None)
            logger.info("%s cache=miss outcome=%s duration_ms=%d", operation, outcome, (monotonic() - started) * 1000)

    async def close(self):
        tasks = tuple(self.in_flight.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

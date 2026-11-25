import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import aiohttp
import aiosqlite
from fastapi import HTTPException
from pydantic import BaseModel

from app.api.shared import combined_car_rate
from app.report_cache import ReportCache
from app.schemas import AuctionQuery, AuctionResponse, Car, CarCompareQuery


class Data(BaseModel):
    value: int


class CacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_auction_lots_with_drom_field_aliases_are_reused(self):
        report = AuctionResponse(
            query=AuctionQuery(firm="toyota", model="rav4", year=2020),
            url="https://www.drom.ru/world/japan/toyota/rav4/",
            examples=[Car(name="Toyota RAV4", productionDate=2020, price_jpy=1_500_000)],
        )
        loader = AsyncMock(return_value=report)
        async with aiosqlite.connect(":memory:") as database:
            cache = ReportCache(database)
            await cache.initialize()
            await cache.get("comparison", report.query, AuctionResponse, loader, timeout=1)
            restored = await cache.get("comparison", report.query, AuctionResponse, loader, timeout=1)
            await database.execute(
                "UPDATE report_cache SET payload = ?", (report.model_dump_json(),)
            )
            await database.commit()
            legacy = await cache.get("comparison", report.query, AuctionResponse, loader, timeout=1)
            self.assertEqual(loader.await_count, 1)
            self.assertEqual(restored, report)
            self.assertEqual(legacy, report)

    async def test_same_work_runs_once_and_cache_survives_reopen_until_expiry(self):
        data = Data(value=1)
        loader = AsyncMock(return_value=data)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cache.db"
            async with aiosqlite.connect(path) as database:
                cache = ReportCache(database)
                await cache.initialize()
                results = await asyncio.gather(*(
                    cache.get("comparison", data, Data, loader, timeout=1)
                    for _ in range(5)
                ))
                self.assertEqual(results, [data] * 5)
                self.assertEqual(loader.await_count, 1)
            async with aiosqlite.connect(path) as database:
                cache = ReportCache(database)
                await cache.initialize()
                self.assertEqual(await cache.get("comparison", data, Data, loader, timeout=1), data)
                self.assertEqual(loader.await_count, 1)
                await database.execute("UPDATE report_cache SET expires_at = 0")
                await database.commit()
                await cache.get("comparison", data, Data, loader, timeout=1)
                self.assertEqual(loader.await_count, 2)

    async def test_partial_results_are_retried_and_heavy_work_is_bounded(self):
        active = peak = 0
        two_started = asyncio.Event()

        async def load():
            nonlocal active, peak
            active += 1
            peak = max(active, peak)
            if active == 2:
                two_started.set()
            await two_started.wait()
            await asyncio.sleep(0.01)
            active -= 1
            return Data(value=99)

        async with aiosqlite.connect(":memory:") as database:
            cache = ReportCache(database)
            await cache.initialize()
            await asyncio.gather(*(
                cache.get("comparison", Data(value=index), Data, load, timeout=5,
                          cacheable=lambda _: False)
                for index in range(6)
            ))
            self.assertEqual(peak, 2)
            async with database.execute("SELECT COUNT(*) FROM report_cache") as cursor:
                self.assertEqual(await cursor.fetchone(), (0,))

    async def test_comparison_forwards_rate_limit_and_blocks_new_upstream_calls(self):
        query = CarCompareQuery(
            firm_id=9, model_id=223, year=2022, modification_id=3238,
            wheel="LEFT", frame="LIFTBACK", region_id=0, import_purpose="USAGE",
        )
        error = aiohttp.ClientResponseError(None, (), status=429, headers={"Retry-After": "120"})
        async with aiosqlite.connect(":memory:") as database:
            cache = ReportCache(database)
            await cache.initialize()
            request = SimpleNamespace(app=SimpleNamespace(
                state=SimpleNamespace(report_cache=cache, comparison_retry_at=0),
            ))
            with patch("app.api.shared.get_combined_compare", AsyncMock(side_effect=error)) as load:
                for params in (query, query.model_copy(update={"year": 2023})):
                    with self.assertRaises(HTTPException) as response:
                        await combined_car_rate(params, request)
                    self.assertEqual(response.exception.status_code, 429)
                    self.assertGreater(int(response.exception.headers["Retry-After"]), 0)
                    self.assertLessEqual(int(response.exception.headers["Retry-After"]), 120)
                self.assertEqual(load.await_count, 1)

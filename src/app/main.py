import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import aiosqlite
from fastapi import FastAPI

from app.api.auctions import router as auctions_router
from app.api.car_rate import router as rate_car_router
from app.api.logs import router as logs_router
from app.api.shared import router as shared_api_router
from app.parser.budget_alternatives import DromAlternatives
from app.parser.budget_photos import BudgetPhotoCache
from app.report_cache import ReportCache


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    database_path = os.getenv("LOG_DATABASE_PATH", ":memory:")
    temporary = TemporaryDirectory() if database_path == ":memory:" else None
    data_directory = Path(temporary.name) if temporary else Path(database_path).parent
    async with aiosqlite.connect(database_path) as database:
        await database.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                created_at TEXT
            )
            """
        )
        async with database.execute("PRAGMA table_info(logs)") as cursor:
            columns = {row[1] for row in await cursor.fetchall()}
        if "created_at" not in columns:
            await database.execute("ALTER TABLE logs ADD COLUMN created_at TEXT")
        cache = ReportCache(database)
        await cache.initialize()
        app.state.database = database
        app.state.report_cache = cache
        app.state.budget_photos = BudgetPhotoCache(data_directory / "budget-photos")
        app.state.drom_alternatives = DromAlternatives(app.state.budget_photos)
        app.state.comparison_retry_at = 0.0
        try:
            yield
        finally:
            await cache.close()
            if temporary:
                temporary.cleanup()


app = FastAPI(lifespan=lifespan)
app.include_router(auctions_router)
app.include_router(rate_car_router)
app.include_router(shared_api_router)
app.include_router(logs_router)


@app.get("/health")
def health() -> dict[str, str | datetime]:
    return {"status": "ok", "timestamp": datetime.now()}
